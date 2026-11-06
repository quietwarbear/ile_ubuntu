"""Kindred → Ile Ubuntu handoff (item X2).

Real code against an in-memory Mongo (mongomock), the same fixture shape as
test_bulk_enrollment.py.
"""

import json
import time
from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import bulk_enrollment
import database
import email_signin
import events
import kindred_handoff
import middleware
from routes import email_notifications
from routes import kindred_handoff as handoff_routes

NOW = datetime.now(timezone.utc)
SECRET = "test-handoff-secret-value"
MODULES = (database, bulk_enrollment, email_signin, events, email_notifications, middleware,
           kindred_handoff, handoff_routes)


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    monkeypatch.setattr(handoff_routes, "rate_limit", lambda *a, **k: None)
    monkeypatch.setenv("KINDRED_HANDOFF_SECRET", SECRET)
    sent = []
    monkeypatch.setattr(email_notifications, "send_paced_in_background", lambda messages: sent.extend(messages))
    mdb.sent = sent
    for key, role in {"owner": "faculty", "otherfaculty": "faculty", "student": "student"}.items():
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test", "subscription_tier": "explorer"})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    for cid, title, owner in (("c-day1", "Day One", "u-owner"), ("c-day2", "Day Two", "u-owner"),
                              ("c-other", "Another Course", "u-otherfaculty")):
        mdb.courses.insert_one({"id": cid, "title": title, "status": "active", "visibility": "private",
                                "instructor_id": owner, "co_instructor_ids": [], "enrolled_count": 0,
                                "created_at": NOW})
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(handoff_routes.router)
    return TestClient(app)


def signed(client, path, payload, *, secret=SECRET, timestamp=None):
    body = json.dumps(payload).encode()
    ts = str(int(timestamp if timestamp is not None else time.time()))
    return client.post(path, content=body, headers={
        "Content-Type": "application/json",
        "X-Handoff-Timestamp": ts,
        "X-Handoff-Signature": kindred_handoff.sign(secret, ts, body),
    })


def owner_key(client):
    response = client.post("/api/kindred-handoff/key", headers={"X-Session-ID": "s-owner"})
    assert response.status_code == 200
    return response.json()["key"]


ATTENDEES = [
    {"name": "Ada Guest", "email": " Ada@Example.test ", "course_ids": ["c-day1", "c-day2"]},
    {"name": "Bea Guest", "email": "bea@example.test", "course_ids": ["c-day2"]},
]


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------


def test_signature_round_trip_and_refusals():
    body = b'{"a":1}'
    ts = str(int(time.time()))
    kindred_handoff.verify_signature(ts, kindred_handoff.sign(SECRET, ts, body), body, secret=SECRET)
    cases = [
        (ts, kindred_handoff.sign("wrong", ts, body), body, 401),
        (ts, kindred_handoff.sign(SECRET, ts, body), b'{"a":2}', 401),
        (str(int(time.time()) - 301), None, body, 401),
        (None, "v1=00", body, 401),
        ("soon", "v1=00", body, 401),
    ]
    for timestamp, signature, payload, status in cases:
        signature = signature or kindred_handoff.sign(SECRET, timestamp, payload)
        with pytest.raises(kindred_handoff.HandoffAuthError) as exc:
            kindred_handoff.verify_signature(timestamp, signature, payload, secret=SECRET)
        assert exc.value.status == status


def test_unconfigured_server_refuses_everything():
    with pytest.raises(kindred_handoff.HandoffAuthError) as exc:
        kindred_handoff.verify_signature("1", "v1=x", b"", secret="")
    assert exc.value.status == 503


def test_unsigned_or_badly_signed_requests_are_refused(client):
    key = owner_key(client)
    assert client.post("/api/kindred-handoff/import", json={"connection_key": key}).status_code == 401
    assert signed(client, "/api/kindred-handoff/import", {"connection_key": key}, secret="nope").status_code == 401
    old = time.time() - 3600
    assert signed(client, "/api/kindred-handoff/import", {"connection_key": key}, timestamp=old).status_code == 401


# ---------------------------------------------------------------------------
# Connection keys
# ---------------------------------------------------------------------------


def test_only_course_staff_can_issue_a_key(client):
    assert client.post("/api/kindred-handoff/key", headers={"X-Session-ID": "s-student"}).status_code == 403


def test_key_is_shown_once_and_only_its_hash_is_stored(client, db):
    key = owner_key(client)
    assert key.startswith("kh_")
    stored = db.kindred_handoff_keys.find_one({"user_id": "u-owner"})
    assert key not in json.dumps(stored, default=str)
    status = client.get("/api/kindred-handoff/key", headers={"X-Session-ID": "s-owner"}).json()
    assert status["active"] is True and status["last4"] == key[-4:] and "key" not in status


def test_new_key_revokes_old_and_revoke_cuts_off(client):
    first = owner_key(client)
    second = owner_key(client)
    assert signed(client, "/api/kindred-handoff/courses", {"connection_key": first}).status_code == 403
    assert signed(client, "/api/kindred-handoff/courses", {"connection_key": second}).status_code == 200
    client.delete("/api/kindred-handoff/key", headers={"X-Session-ID": "s-owner"})
    assert signed(client, "/api/kindred-handoff/courses", {"connection_key": second}).status_code == 403


@pytest.mark.parametrize("key", [None, "", "not-a-key", "kh_unknown"])
def test_bad_keys_are_refused_the_same_way(client, key):
    response = signed(client, "/api/kindred-handoff/courses", {"connection_key": key})
    assert response.status_code == 403


def test_courses_lists_only_what_the_teacher_runs(client):
    key = owner_key(client)
    response = signed(client, "/api/kindred-handoff/courses", {"connection_key": key}).json()
    assert [c["id"] for c in response["courses"]] == ["c-day1", "c-day2"]
    assert response["teacher_name"] == "Owner"


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def test_import_creates_enrolls_and_sends_welcome(client, db):
    key = owner_key(client)
    report = signed(client, "/api/kindred-handoff/import",
                    {"connection_key": key, "event_ref": "ev-1", "attendees": ATTENDEES}).json()
    assert report["counts"] == {"created": 2, "enrolled": 3, "skipped": 0, "errors": 0}
    ada = db.users.find_one({"email": "ada@example.test"})
    assert ada["auth_provider"] == "invited"
    assert {e["course_id"] for e in db.enrollments.find({"user_id": ada["id"]})} == {"c-day1", "c-day2"}
    assert all(e["source"] == "import" for e in db.enrollments.find())
    assert report["welcome_emails"] == 2 and len(db.sent) == 2


def test_rerun_is_idempotent_and_adds_only_new(client, db):
    key = owner_key(client)
    signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": ATTENDEES})
    db.sent.clear()
    more = ATTENDEES + [{"name": "Cy Guest", "email": "cy@example.test", "course_ids": ["c-day1"]}]
    report = signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": more}).json()
    assert report["counts"] == {"created": 1, "enrolled": 1, "skipped": 3, "errors": 0}
    assert db.users.count_documents({}) == 6 and db.enrollments.count_documents({}) == 4
    assert len(db.sent) == 1


def test_dry_run_writes_nothing(client, db):
    key = owner_key(client)
    report = signed(client, "/api/kindred-handoff/import",
                    {"connection_key": key, "attendees": ATTENDEES, "dry_run": True}).json()
    assert report["dry_run"] is True and report["counts"]["enrolled"] == 3
    assert db.enrollments.count_documents({}) == 0 and db.users.count_documents({}) == 3
    assert db.sent == []


def test_courses_the_teacher_does_not_run_are_unknown(client, db):
    key = owner_key(client)
    attendees = [{"name": "Ada", "email": "ada@example.test", "course_ids": ["c-other"]},
                 {"name": "Bea", "email": "bea@example.test", "course_ids": ["c-day1"]}]
    report = signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": attendees}).json()
    assert report["counts"]["enrolled"] == 1
    assert report["errors"] == [{"row": 1, "email": "ada@example.test", "error": "Unknown session: c-other"}]
    assert db.enrollments.count_documents({"course_id": "c-other"}) == 0


def test_bad_rows_are_reported_not_fatal(client):
    key = owner_key(client)
    attendees = ["nope", {"name": "No Email", "course_ids": ["c-day1"]},
                 {"name": "No courses", "email": "x@example.test", "course_ids": []},
                 {"name": "Ok", "email": "ok@example.test", "course_ids": ["c-day1"]}]
    report = signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": attendees}).json()
    assert [e["row"] for e in report["errors"]] == [1, 2, 3]
    assert report["counts"]["enrolled"] == 1


def test_attendees_must_be_a_bounded_list(client, monkeypatch):
    key = owner_key(client)
    assert signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": "x"}).status_code == 400
    monkeypatch.setattr(kindred_handoff, "MAX_ROWS", 1)
    response = signed(client, "/api/kindred-handoff/import", {"connection_key": key, "attendees": ATTENDEES})
    assert response.status_code == 413


def test_signature_matches_the_shared_vector():
    # The same vector is asserted in kindred backend/tests/test_x2_ile_ubuntu_handoff.py,
    # so a format change on either side fails both suites.
    import kindred_handoff as kh

    assert kh.sign("shared-test-secret", "1700000000", b'{"a":1}') == (
        "v1=b69bcc2b6b3690a8440616579fa827f9c8fe67d9a4458e144a51d646751f8100"
    )
