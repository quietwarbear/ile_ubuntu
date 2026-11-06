"""Cloudflare Stream video and captions (items I4 phase 2 and I5).

Real routes against an in-memory Mongo (mongomock). Cloudflare is faked at
the single HTTP seam (stream._request); signing uses a throwaway RSA key.
"""

import base64
import json
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import mongomock
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import database
import file_access
import middleware
import migrate_videos_to_stream as migration
import storage
import stream
from routes import courses, files, stream_video

NOW = datetime.now(timezone.utc)
MODULES = (database, file_access, middleware, migration, courses, files, stream_video)
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption()).decode()


class FakeCloudflare:
    def __init__(self):
        self.calls = []
        self.videos = {}
        self.captions = {}
        self.bodies = {}

    def __call__(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        req = httpx.Request(method, "https://api.cloudflare.test" + path)

        def ok(result, status=200, headers=None):
            return httpx.Response(status, json={"success": True, "result": result},
                                  headers=headers, request=req)

        if method == "POST" and path == "?direct_user=true":
            uid = f"uid{len(self.videos) + 1}"
            self.videos[uid] = {"uid": uid, "readyToStream": False, "status": {"state": "queued"},
                                "requireSignedURLs": True}
            return httpx.Response(201, headers={"Location": f"https://upload.test/{uid}",
                                                "stream-media-id": uid}, request=req)
        if method == "POST" and path == "/copy":
            uid = f"copy{len(self.videos) + 1}"
            self.videos[uid] = {"uid": uid, "readyToStream": False, "status": {"state": "queued"},
                                "requireSignedURLs": True}
            return ok({"uid": uid})
        uid, _, rest = path.lstrip("/").partition("/")
        if not rest:
            if method == "GET":
                return ok(self.videos[uid])
            if method == "POST":
                self.videos[uid].update(kwargs["json"])
                return ok(self.videos[uid])
            if method == "DELETE":
                self.videos.pop(uid, None)
                return httpx.Response(200, request=req)
        if rest == "captions" and method == "GET":
            return ok(list(self.captions.get(uid, {}).values()))
        parts = rest.split("/")
        lang = parts[1]
        if parts[-1] == "generate":
            self.captions.setdefault(uid, {})[lang] = {"language": lang, "label": lang,
                                                      "generated": True, "status": "inprogress"}
            return ok(self.captions[uid][lang])
        if parts[-1] == "vtt":
            return httpx.Response(200, text="WEBVTT\n\n00:00.000 --> 00:01.000\nHello", request=req)
        if method == "PUT":
            self.captions.setdefault(uid, {})[lang] = {"language": lang, "label": lang,
                                                      "generated": False, "status": "ready"}
            self.bodies[(uid, lang)] = kwargs["files"]["file"][1]
            return ok(self.captions[uid][lang])
        if method == "DELETE":
            self.captions.get(uid, {}).pop(lang, None)
            return httpx.Response(200, request=req)
        raise AssertionError(f"unexpected call {method} {path}")


@pytest.fixture
def cf(monkeypatch):
    fake = FakeCloudflare()
    monkeypatch.setattr(stream, "_request", fake)
    for name, value in {"CF_ACCOUNT_ID": "acct", "CF_STREAM_API_TOKEN": "tok",
                        "CF_STREAM_CUSTOMER_CODE": "abc123", "CF_STREAM_SIGNING_KEY_ID": "kid1",
                        "CF_STREAM_SIGNING_KEY_PEM": base64.b64encode(PEM.encode()).decode()}.items():
        monkeypatch.setenv(name, value)
    return fake


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    for key, role in (("teacher", "faculty"), ("student", "student"), ("outsider", "student")):
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title()})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    mdb.courses.insert_one({"id": "c1", "title": "Course", "instructor_id": "u-teacher",
                            "co_instructor_ids": [], "status": "active"})
    mdb.lessons.insert_one({"id": "l1", "course_id": "c1", "title": "Day one", "order": 1})
    mdb.enrollments.insert_one({"user_id": "u-student", "course_id": "c1"})
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    for module in (files, stream_video, courses):
        app.include_router(module.router)
    return TestClient(app, follow_redirects=False)


def as_(who):
    return {"X-Session-ID": f"s-{who}"}


def start(client, size=3_000_000_000):
    res = client.post("/api/stream/uploads", headers=as_("teacher"), json={
        "course_id": "c1", "lesson_id": "l1", "size": size, "filename": "talk.mov",
        "mime_type": "video/quicktime"})
    assert res.status_code == 200, res.text
    return res.json()


def make_ready(cf, db, uid="uid1", duration=7200.0):
    cf.videos[uid].update({"readyToStream": True, "status": {"state": "ready"}, "duration": duration})
    db.files.update_one({"stream_uid": uid}, {"$unset": {"stream_checked_at": ""}})


# --- off by default -------------------------------------------------------------------

def test_unconfigured_stream_is_off_and_old_path_untouched(client, monkeypatch):
    for name in ("CF_ACCOUNT_ID", "CF_STREAM_API_TOKEN", "CF_STREAM_CUSTOMER_CODE",
                 "CF_STREAM_SIGNING_KEY_ID", "CF_STREAM_SIGNING_KEY_PEM"):
        monkeypatch.delenv(name, raising=False)
    assert stream.enabled() is False
    assert client.get("/api/stream/config", headers=as_("teacher")).json()["enabled"] is False
    res = client.post("/api/stream/uploads", headers=as_("teacher"),
                      json={"course_id": "c1", "size": 10, "filename": "x.mp4"})
    assert res.status_code == 404


def test_partial_config_is_still_off(cf, monkeypatch):
    monkeypatch.delenv("CF_STREAM_SIGNING_KEY_PEM")
    assert stream.enabled() is False


# --- upload ---------------------------------------------------------------------------

def test_staff_get_a_resumable_upload_url_and_a_file_record(client, cf, db):
    body = start(client)
    assert body["upload_url"] == "https://upload.test/uid1"
    method, path, kwargs = cf.calls[0]
    assert kwargs["headers"]["Upload-Length"] == "3000000000"
    assert "requiresignedurls" in kwargs["headers"]["Upload-Metadata"].split(",")
    record = db.files.find_one({"id": body["file_id"]})
    assert record["stream_uid"] == "uid1" and record["storage"] == "stream"
    assert record["file_category"] == "video" and "s3_key" not in record
    assert body["file_id"] in db.lessons.find_one({"id": "l1"})["files"]


def test_only_course_staff_can_upload(client, cf):
    res = client.post("/api/stream/uploads", headers=as_("student"),
                      json={"course_id": "c1", "size": 10, "filename": "x.mp4"})
    assert res.status_code == 403
    res = client.post("/api/stream/uploads", headers=as_("teacher"),
                      json={"course_id": "c1", "size": 10, "mime_type": "application/pdf"})
    assert res.status_code == 400


# --- playback -------------------------------------------------------------------------

def tokens(client, who, file_id):
    return client.post("/api/files/access-tokens", headers=as_(who), json={"file_ids": [file_id]}).json()


def test_processing_then_ready_with_signed_short_lived_urls(client, cf, db):
    fid = start(client)["file_id"]
    assert tokens(client, "student", fid)["tokens"][fid]["stream"] == {"state": "queued"}

    make_ready(cf, db)
    playback = tokens(client, "student", fid)["tokens"][fid]["stream"]
    assert playback["state"] == "ready"
    assert playback["iframe_url"].startswith("https://customer-abc123.cloudflarestream.com/")
    assert "defaultTextTrack" not in playback["iframe_url"]           # captions start off
    token = playback["hls_url"].split("/")[3]
    claims = jwt.decode(token, KEY.public_key(), algorithms=["RS256"])
    assert claims["sub"] == "uid1" and jwt.get_unverified_header(token)["kid"] == "kid1"
    ttl = claims["exp"] - datetime.now(timezone.utc).timestamp()
    assert 7200 + 500 < ttl <= 7200 + 600 + 5                          # watch once, then useless


def test_token_lifetime_is_capped(cf):
    assert stream.playback_ttl(50 * 3600) == stream.MAX_PLAYBACK_TTL
    assert stream.playback_ttl(None) == 600


def test_no_signed_url_for_people_without_access(client, cf, db):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    assert tokens(client, "outsider", fid)["tokens"] == {}
    assert client.get(f"/api/files/{fid}/stream").status_code == 401


def test_ready_video_turns_on_auto_captions_and_forces_signing(client, cf, db):
    fid = start(client)["file_id"]
    cf.videos["uid1"]["requireSignedURLs"] = False
    make_ready(cf, db)
    tokens(client, "student", fid)
    assert cf.videos["uid1"]["requireSignedURLs"] is True
    assert cf.captions["uid1"]["en"]["generated"] is True
    assert db.files.find_one({"id": fid})["auto_captions_requested"] == "en"
    generate_calls = [c for c in cf.calls if c[1].endswith("/generate")]
    db.files.update_one({"id": fid}, {"$unset": {"stream_checked_at": ""}, "$set": {"stream_ready": False}})
    tokens(client, "student", fid)
    assert len([c for c in cf.calls if c[1].endswith("/generate")]) == len(generate_calls)   # only once


def test_old_token_url_redirects_to_signed_manifest(client, cf, db):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    url = tokens(client, "student", fid)["tokens"][fid]["url"]
    res = client.get(url)
    assert res.status_code == 307 and res.headers["location"].endswith("/manifest/video.m3u8")


def test_stream_record_says_unavailable_if_config_is_removed(client, cf, db, monkeypatch):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    monkeypatch.delenv("CF_STREAM_API_TOKEN")
    assert tokens(client, "student", fid)["tokens"][fid]["stream"] == {"state": "unavailable"}


def test_access_end_date_also_stops_stream_tokens(client, cf, db):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    db.courses.update_one({"id": "c1"}, {"$set": {"access_ends_at": NOW - timedelta(days=1)}})
    body = tokens(client, "student", fid)
    assert body["tokens"] == {} and body["ended"][fid].startswith("access_ended:")


def test_deleting_the_file_deletes_the_stream_video(client, cf, db):
    fid = start(client)["file_id"]
    assert client.delete(f"/api/files/{fid}", headers=as_("teacher")).status_code == 200
    assert "uid1" not in cf.videos


def test_integrity_report_ignores_stream_videos(client, cf, db):
    start(client)
    report = client.get("/api/files/integrity/report", headers=as_("teacher")).json()
    assert report["local_records"] == 0


# --- captions (I5) --------------------------------------------------------------------

def test_staff_upload_edit_and_remove_a_vtt(client, cf, db):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    client.post(f"/api/stream/{fid}/refresh", headers=as_("teacher"))
    vtt = "WEBVTT\n\n00:00.000 --> 00:02.000\nWelcome"
    assert client.put(f"/api/stream/{fid}/captions/es", headers=as_("teacher"),
                      json={"vtt": vtt}).status_code == 200
    assert cf.bodies[("uid1", "es")] == vtt.encode()
    listed = client.get(f"/api/stream/{fid}/captions", headers=as_("teacher")).json()
    assert {t["language"] for t in listed["captions"]} == {"en", "es"}
    assert client.get(f"/api/stream/{fid}/captions/en/vtt", headers=as_("teacher")).json()["vtt"].startswith("WEBVTT")
    assert client.delete(f"/api/stream/{fid}/captions/es", headers=as_("teacher")).status_code == 200
    assert "es" not in cf.captions["uid1"]


def test_caption_input_is_checked(client, cf, db):
    fid = start(client)["file_id"]
    make_ready(cf, db)
    client.post(f"/api/stream/{fid}/refresh", headers=as_("teacher"))
    assert client.put(f"/api/stream/{fid}/captions/en", headers=as_("teacher"),
                      json={"vtt": "1\n00:00:00,000 --> ..."}).status_code == 400   # SRT, not VTT
    assert client.put(f"/api/stream/{fid}/captions/../x", headers=as_("teacher"),
                      json={"vtt": "WEBVTT"}).status_code in (400, 404)
    assert client.post(f"/api/stream/{fid}/captions/sw/generate",
                       headers=as_("teacher")).status_code == 400              # not a supported language


def test_generate_waits_for_processing(client, cf, db):
    fid = start(client)["file_id"]
    assert client.post(f"/api/stream/{fid}/captions/en/generate", headers=as_("teacher")).status_code == 409


def test_students_cannot_manage_captions(client, cf, db):
    fid = start(client)["file_id"]
    for res in (client.get(f"/api/stream/{fid}/captions", headers=as_("student")),
                client.put(f"/api/stream/{fid}/captions/en", headers=as_("student"), json={"vtt": "WEBVTT"})):
        assert res.status_code == 403


# --- migration script ------------------------------------------------------------------

def test_migration_dry_run_changes_nothing(cf, db, capsys):
    db.files.insert_many([
        {"id": "f-s3", "file_category": "video", "s3_key": "uploads/a.mp4", "original_filename": "a.mp4",
         "file_size": 5_000_000, "uploaded_at": NOW},
        {"id": "f-disk", "file_category": "video", "file_path": "uploads/b.mp4", "original_filename": "b.mp4",
         "uploaded_at": NOW},
    ])
    assert migration.main([]) == 0
    out = capsys.readouterr().out
    assert "[DRY RUN] 1 video(s)" in out and "move  f-s3" in out and "skip  f-disk" in out
    assert cf.calls == []
    assert "stream_uid" not in db.files.find_one({"id": "f-s3"})


def test_migration_apply_copies_and_keeps_the_original(cf, db, monkeypatch, capsys):
    db.files.insert_one({"id": "f-s3", "file_category": "video", "s3_key": "uploads/a.mp4",
                         "original_filename": "a.mp4", "uploaded_at": NOW})
    monkeypatch.setattr(storage, "s3_enabled", lambda: True)
    monkeypatch.setattr(storage, "presigned_get", lambda key, *a, **k: f"https://bucket.test/{key}")
    assert migration.main(["--apply"]) == 0
    record = db.files.find_one({"id": "f-s3"})
    assert record["stream_uid"].startswith("copy") and record["legacy_s3_key"] == "uploads/a.mp4"
    assert "s3_key" not in record
    copy_call = next(c for c in cf.calls if c[1] == "/copy")
    assert copy_call[2]["json"]["url"] == "https://bucket.test/uploads/a.mp4"
    assert copy_call[2]["json"]["requireSignedURLs"] is True
