"""Access control on /api/files (item I4, phase 1).

Runs the real routes against an in-memory Mongo (mongomock), so it needs no
server and no database. Every collection the access rule reads is swapped for
the same mongomock database.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import file_access
import middleware
import storage
from routes import courses as courses_routes
from routes import files as files_routes

NOW = datetime.now(timezone.utc)

COLLECTIONS = {
    file_access: ["courses_col", "enrollments_col", "family_links_col", "lessons_col",
                  "portfolio_items_col", "submissions_col"],
    files_routes: ["files_col", "lessons_col", "courses_col", "users_col"],
    middleware: ["sessions_col", "users_col"],
    courses_routes: ["courses_col", "lessons_col", "files_col", "enrollments_col"],
}


@pytest.fixture
def db(monkeypatch, tmp_path):
    mdb = mongomock.MongoClient().db
    for module, names in COLLECTIONS.items():
        for name in names:
            monkeypatch.setattr(module, name, mdb[name.removesuffix("_col")])

    # A real file on disk so a granted request returns 200.
    doc = tmp_path / "notes.pdf"
    doc.write_bytes(b"%PDF-1.4 test")
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    users = {
        "teacher": {"id": "u-teacher", "role": "faculty", "name": "Teacher"},
        "student": {"id": "u-student", "role": "student", "name": "Enrolled"},
        "outsider": {"id": "u-outsider", "role": "student", "name": "Outsider"},
        "admin": {"id": "u-admin", "role": "admin", "name": "Admin"},
    }
    for key, user in users.items():
        mdb.users.insert_one(dict(user))
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": user["id"],
                                 "expires_at": NOW + timedelta(days=1)})

    mdb.courses.insert_one({"id": "c1", "title": "Course", "instructor_id": "u-teacher",
                            "status": "active"})
    mdb.enrollments.insert_one({"user_id": "u-student", "course_id": "c1"})
    mdb.lessons.insert_many([
        {"id": "l-open", "course_id": "c1", "title": "Open", "video_file_id": "f-video",
         "content": "See the handout /api/files/f-embed/download?file=x.pdf"},
        {"id": "l-hidden", "course_id": "c1", "title": "Hidden", "hidden": True},
    ])
    base = {"uploaded_by": "u-teacher", "mime_type": "application/pdf",
            "file_category": "document", "original_filename": "notes.pdf",
            "file_path": str(doc), "storage": "local"}
    mdb.files.insert_many([
        {**base, "id": "f-attach", "lesson_id": "l-open", "course_id": "c1"},
        {**base, "id": "f-course", "course_id": "c1"},
        {**base, "id": "f-embed"},  # uploaded from the editor: no course on the record
        {**base, "id": "f-hidden", "lesson_id": "l-hidden", "course_id": "c1"},
        {**base, "id": "f-public", "visibility": "public"},
        {**base, "id": "f-video", "lesson_id": "l-open", "course_id": "c1",
         "mime_type": "video/mp4", "file_category": "video", "file_path": str(video),
         "original_filename": "talk.mp4"},
    ])
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(files_routes.router)
    return TestClient(app, follow_redirects=False)


def hdr(who):
    return {"X-Session-ID": f"s-{who}"}


def token(client, who, file_id):
    res = client.post("/api/files/access-tokens", json={"file_ids": [file_id]}, headers=hdr(who))
    assert res.status_code == 200
    return res.json()["tokens"].get(file_id)


# --- the core rule ------------------------------------------------------------

def test_no_credentials_is_refused(client):
    assert client.get("/api/files/f-attach/download").status_code == 401
    assert client.get("/api/files/f-video/stream").status_code == 401


@pytest.mark.parametrize("file_id", ["f-attach", "f-course", "f-embed", "f-hidden"])
def test_unenrolled_user_gets_403(client, file_id):
    assert client.get(f"/api/files/{file_id}/download", headers=hdr("outsider")).status_code == 403


def test_unenrolled_user_cannot_stream_video(client):
    assert client.get("/api/files/f-video/stream", headers=hdr("outsider")).status_code == 403


@pytest.mark.parametrize("file_id", ["f-attach", "f-course", "f-embed"])
def test_enrolled_user_gets_the_file(client, file_id):
    assert client.get(f"/api/files/{file_id}/download", headers=hdr("student")).status_code == 200


def test_enrolled_user_streams_video(client):
    res = client.get("/api/files/f-video/stream", headers=hdr("student"))
    assert res.status_code == 200
    assert res.headers["content-disposition"].startswith("inline")


def test_video_never_downloads_as_attachment(client):
    res = client.get("/api/files/f-video/download", headers=hdr("student"))
    assert res.headers["content-disposition"].startswith("inline")


def test_file_on_hidden_lesson_is_withheld_from_students_not_staff(client):
    assert client.get("/api/files/f-hidden/download", headers=hdr("student")).status_code == 403
    assert client.get("/api/files/f-hidden/download", headers=hdr("teacher")).status_code == 200


def test_admin_passes(client):
    assert client.get("/api/files/f-attach/download", headers=hdr("admin")).status_code == 200


def test_public_asset_still_loads_for_anyone(client):
    assert client.get("/api/files/f-public/download").status_code == 200


def test_unenrolling_takes_effect_immediately(client, db):
    tok = token(client, "student", "f-attach")
    db.enrollments.delete_many({"user_id": "u-student"})
    assert client.get(f"/api/files/f-attach/download?t={tok['token']}").status_code == 403


# --- playback tokens ----------------------------------------------------------

def test_token_lets_a_tag_load_without_the_header(client):
    tok = token(client, "student", "f-video")
    assert tok["url"].startswith("/api/files/f-video/stream?t=")
    assert client.get(tok["url"]).status_code == 200


def test_token_is_not_issued_for_files_you_cannot_read(client):
    assert token(client, "outsider", "f-attach") is None


def test_expired_token_is_refused(client):
    stale = file_access.issue_token("u-student", "f-attach", now=NOW - timedelta(hours=1))
    assert client.get(f"/api/files/f-attach/download?t={stale['token']}").status_code == 403


def test_forged_token_is_refused(client):
    import jwt
    forged = jwt.encode({"sub": "u-student", "fid": "f-attach", "aud": file_access.TOKEN_AUDIENCE,
                         "exp": int((NOW + timedelta(minutes=5)).timestamp())},
                        "not-the-secret", algorithm="HS256")
    assert client.get(f"/api/files/f-attach/download?t={forged}").status_code == 403
    assert client.get("/api/files/f-attach/download?t=garbage").status_code == 403


def test_token_for_another_file_is_refused(client):
    tok = token(client, "student", "f-course")
    assert client.get(f"/api/files/f-attach/download?t={tok['token']}").status_code == 403


def test_other_users_token_is_refused(client):
    tok = token(client, "student", "f-attach")
    res = client.get(f"/api/files/f-attach/download?t={tok['token']}", headers=hdr("outsider"))
    assert res.status_code == 403


def test_token_lifetime_is_at_most_ten_minutes():
    issued = file_access.issue_token("u", "f")
    exp = datetime.fromisoformat(issued["expires_at"])
    assert exp - datetime.now(timezone.utc) <= timedelta(minutes=10)


# --- listings and S3 ----------------------------------------------------------

def test_listing_hides_course_files_from_outsiders(client):
    res = client.get("/api/files?course_id=c1", headers=hdr("outsider"))
    assert res.json()["files"] == []


def test_listing_gives_enrolled_users_working_signed_urls(client):
    files = client.get("/api/files?lesson_id=l-open", headers=hdr("student")).json()["files"]
    assert {f["id"] for f in files} == {"f-attach", "f-video"}
    for f in files:
        assert "?t=" in f["download_url"]
        assert client.get(f["download_url"]).status_code == 200


def test_s3_video_gets_short_inline_presign(client, db, monkeypatch):
    seen = {}

    def fake_presign(key, filename, content_type, inline=True, ttl=None):
        seen.update(inline=inline, ttl=ttl)
        return "https://bucket.example/obj"

    monkeypatch.setattr(storage, "presigned_get", fake_presign)
    db.files.update_one({"id": "f-video"}, {"$set": {"s3_key": "uploads/f-video.mp4"}})
    res = client.get("/api/files/f-video/stream", headers=hdr("student"))
    assert res.status_code == 307
    assert seen == {"inline": True, "ttl": storage.VIDEO_PRESIGN_TTL}
    assert storage.VIDEO_PRESIGN_TTL <= 600


def test_no_public_uploads_mount():
    server_src = (Path(__file__).resolve().parents[1] / "server.py").read_text()
    assert 'app.mount("/uploads"' not in server_src


def test_submission_file_is_for_its_student_and_teacher_only(client, db):
    db.submissions.insert_one({"id": "sub1", "student_id": "u-student", "course_id": "c1",
                               "lesson_id": "l-open"})
    db.files.update_one({"id": "f-course"}, {"$set": {"submission_id": "sub1",
                                                      "uploaded_by": "u-student"},
                                             "$unset": {"course_id": ""}})
    db.enrollments.insert_one({"user_id": "u-outsider", "course_id": "c1"})
    assert client.get("/api/files/f-course/download", headers=hdr("student")).status_code == 200
    assert client.get("/api/files/f-course/download", headers=hdr("teacher")).status_code == 200
    # Being enrolled in the same course does not open a classmate's work.
    assert client.get("/api/files/f-course/download", headers=hdr("outsider")).status_code == 403


def test_portfolio_file_opens_to_guardian_only_when_shared(client, db):
    db.files.update_one({"id": "f-public"}, {"$set": {"uploaded_by": "u-student"},
                                             "$unset": {"visibility": ""}})
    db.family_links.insert_one({"guardian_id": "u-outsider", "youth_id": "u-student"})
    db.portfolio_items.insert_one({"id": "p1", "user_id": "u-student", "file_id": "f-public",
                                   "visibility": "private"})
    assert client.get("/api/files/f-public/download", headers=hdr("outsider")).status_code == 403
    db.portfolio_items.update_one({"id": "p1"}, {"$set": {"visibility": "shared"}})
    assert client.get("/api/files/f-public/download", headers=hdr("outsider")).status_code == 200


def test_platform_faculty_cannot_open_files_on_a_private_course(client, db):
    db.users.insert_one({"id": "u-faculty2", "role": "faculty", "name": "Other teacher"})
    db.sessions.insert_one({"session_id": "s-faculty2", "user_id": "u-faculty2",
                            "expires_at": NOW + timedelta(days=1)})
    assert client.get("/api/files/f-attach/download", headers=hdr("faculty2")).status_code == 200
    db.courses.update_one({"id": "c1"}, {"$set": {"visibility": "private"}})
    assert client.get("/api/files/f-attach/download", headers=hdr("faculty2")).status_code == 403
    assert client.get("/api/files/f-attach/download", headers=hdr("student")).status_code == 200
