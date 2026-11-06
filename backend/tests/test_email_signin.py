"""Emailed sign-in links, the import welcome email, and send logging (I3).

Real code against an in-memory Mongo (mongomock). Resend is never called.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import bulk_enrollment
import database
import email_signin
import events
import middleware
from routes import auth, email_notifications

NOW = datetime.now(timezone.utc)
MODULES = (database, bulk_enrollment, email_signin, events, middleware, auth, email_notifications)


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    monkeypatch.setattr(auth, "rate_limit", lambda *a, **k: None)
    for key, role in (("ada", "student"), ("admin", "admin"), ("owner", "faculty")):
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test", "email_verified": False})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    return mdb


@pytest.fixture
def outbox(monkeypatch):
    """Every send_email call, captured instead of going to Resend."""
    sent = []

    async def fake_send(to, subject, html, kind="general"):
        sent.append(SimpleNamespace(to=to, subject=subject, html=html, kind=kind))
        return {"id": "re_test"}
    monkeypatch.setattr(email_notifications, "send_email", fake_send)
    return sent


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(email_notifications.router)
    return TestClient(app)


def token_from(html):
    return html.split("signin-link?token=")[1].split('"')[0].split("&")[0]


# --- token rules ---------------------------------------------------------------------

def test_token_is_single_use(db):
    token = email_signin.issue_token("u-ada")
    assert email_signin.redeem_token(token)["id"] == "u-ada"
    assert email_signin.redeem_token(token) is None


def test_token_expires_after_15_minutes(db):
    token = email_signin.issue_token("u-ada", now=NOW - timedelta(minutes=16))
    assert email_signin.token_state(token) == "expired"
    assert email_signin.redeem_token(token) is None


def test_token_works_until_expiry(db):
    token = email_signin.issue_token("u-ada", now=NOW - timedelta(minutes=14))
    assert email_signin.redeem_token(token)["id"] == "u-ada"


def test_welcome_token_lasts_three_days(db):
    token = email_signin.issue_token("u-ada", "welcome", now=NOW - timedelta(days=2, hours=23))
    assert email_signin.token_state(token) == "valid"
    stale = email_signin.issue_token("u-ada", "welcome", now=NOW - timedelta(days=3, minutes=1))
    assert email_signin.token_state(stale) == "expired"


def test_only_a_hash_is_stored(db):
    token = email_signin.issue_token("u-ada")
    row = db.email_signin_tokens.find_one()
    assert token not in str(row)


def test_forged_or_empty_token_fails(db):
    email_signin.issue_token("u-ada")
    assert email_signin.redeem_token("not-a-real-token") is None
    assert email_signin.redeem_token("") is None
    assert email_signin.redeem_token(None) is None
    assert email_signin.token_state("not-a-real-token") == "unknown"


def test_redeeming_marks_the_email_verified(db):
    email_signin.redeem_token(email_signin.issue_token("u-ada"))
    assert db.users.find_one({"id": "u-ada"})["email_verified"] is True


# --- routes ----------------------------------------------------------------------------

def test_request_link_then_sign_in(client, db, outbox):
    res = client.post("/api/auth/email-link", json={"email": "  ADA@example.test "})
    assert res.status_code == 200
    assert len(outbox) == 1 and outbox[0].to == "ada@example.test" and outbox[0].kind == "signin_link"
    token = token_from(outbox[0].html)
    assert client.post("/api/auth/email-link/status", json={"token": token}).json() == {"state": "valid"}

    first = client.post("/api/auth/email-link/redeem", json={"token": token})
    assert first.status_code == 200 and first.json()["user_id"] == "u-ada"
    assert db.sessions.find_one({"session_id": first.json()["session_id"]})["user_id"] == "u-ada"

    again = client.post("/api/auth/email-link/redeem", json={"token": token})
    assert again.status_code == 400
    assert client.post("/api/auth/email-link/status", json={"token": token}).json() == {"state": "used"}


def test_unknown_address_gets_the_same_answer_and_no_email(client, outbox):
    known = client.post("/api/auth/email-link", json={"email": "ada@example.test"}).json()
    unknown = client.post("/api/auth/email-link", json={"email": "nobody@example.test"}).json()
    assert known == unknown
    assert [m.to for m in outbox] == ["ada@example.test"]


def test_link_from_the_app_says_so(client, outbox):
    client.post("/api/auth/email-link", json={"email": "ada@example.test", "app": True})
    assert "&app=1" in outbox[0].html


def test_per_address_limit(client, db, outbox):
    for _ in range(email_signin.MAX_LINKS_PER_ADDRESS + 2):
        assert client.post("/api/auth/email-link", json={"email": "ada@example.test"}).status_code == 200
    assert len(outbox) == email_signin.MAX_LINKS_PER_ADDRESS


def test_request_is_rate_limited_per_ip(db, outbox, monkeypatch):
    from rate_limit import rate_limit as real_limit
    monkeypatch.setattr(auth, "rate_limit", real_limit)
    import rate_limit as rl
    rl._hits.clear() if hasattr(rl, "_hits") else None
    app = FastAPI()
    app.include_router(auth.router)
    c = TestClient(app)
    codes = [c.post("/api/auth/email-link", json={"email": f"x{i}@example.test"}).status_code
             for i in range(7)]
    assert 429 in codes


def test_bad_request(client):
    assert client.post("/api/auth/email-link", json={"email": ""}).status_code == 400


# --- welcome email from the I1 import ---------------------------------------------------

@pytest.fixture
def paced(monkeypatch):
    queued = []
    monkeypatch.setattr(email_notifications, "send_paced_in_background",
                        lambda messages: queued.extend(messages))
    return queued


@pytest.fixture
def courses(db):
    for cid, title in (("c-1", "Morning <Circle>"), ("c-2", "Evening Circle")):
        db.courses.insert_one({"id": cid, "title": title, "instructor_id": "u-owner",
                               "co_instructor_ids": [], "status": "active", "visibility": "private"})


OWNER = {"id": "u-owner", "role": "faculty"}


def test_import_sends_one_welcome_per_person_naming_their_courses(db, courses, paced):
    report = bulk_enrollment.import_enrollments([
        {"row": 2, "name": "New Person", "email": "new@example.test", "sessions": ["c-1", "c-2"]},
        {"row": 3, "name": "Ada", "email": "ada@example.test", "sessions": ["c-2"]},
    ], {}, OWNER)
    assert report["welcome_emails"] == 2
    by_to = {m[0]: m for m in paced}
    to, subject, html, kind = by_to["new@example.test"]
    assert kind == "welcome" and subject == "You're enrolled in 2 courses"
    assert "Morning &lt;Circle&gt;" in html and "Evening Circle" in html   # escaped
    assert by_to["ada@example.test"][1] == "You're enrolled: Evening Circle"
    # the link signs the new, password-less person in
    user = email_signin.redeem_token(token_from(html))
    assert user["email"] == "new@example.test"


def test_rerun_that_adds_nothing_sends_nothing(db, courses, paced):
    rows = [{"name": "Ada", "email": "ada@example.test", "sessions": ["c-1"]}]
    bulk_enrollment.import_enrollments(rows, {}, OWNER)
    paced.clear()
    report = bulk_enrollment.import_enrollments(rows, {}, OWNER)
    assert report["welcome_emails"] == 0 and paced == []


def test_rerun_that_adds_a_course_mentions_only_the_new_one(db, courses, paced):
    bulk_enrollment.import_enrollments([{"email": "ada@example.test", "sessions": ["c-1"]}], {}, OWNER)
    paced.clear()
    bulk_enrollment.import_enrollments([{"email": "ada@example.test", "sessions": ["c-1", "c-2"]}], {}, OWNER)
    assert len(paced) == 1 and paced[0][1] == "You're enrolled: Evening Circle"


def test_dry_run_and_opt_out_send_nothing(db, courses, paced):
    rows = [{"email": "ada@example.test", "sessions": ["c-1"]}]
    assert bulk_enrollment.import_enrollments(rows, {}, OWNER, dry_run=True)["welcome_emails"] == 0
    assert bulk_enrollment.import_enrollments(rows, {}, OWNER, send_welcome=False)["welcome_emails"] == 0
    assert paced == []


# --- delivery logging ---------------------------------------------------------------------

def run_send(**kw):
    import asyncio
    return asyncio.run(email_notifications.send_email("Ada@Example.test", "Hi", "<p>x</p>", **kw))


def test_send_without_api_key_is_logged_as_not_configured(db, monkeypatch):
    monkeypatch.setattr(email_notifications, "RESEND_API_KEY", None)
    assert run_send(kind="welcome") is None
    row = db.email_log.find_one()
    assert row["status"] == "not_configured" and row["kind"] == "welcome" and row["to"] == "ada@example.test"


def test_successful_send_records_the_resend_id(db, monkeypatch, caplog):
    monkeypatch.setattr(email_notifications, "RESEND_API_KEY", "re_key")
    monkeypatch.setattr(email_notifications.resend.Emails, "send", lambda params: {"id": "re_123"})
    with caplog.at_level("INFO"):
        run_send(kind="signin_link")
    row = db.email_log.find_one()
    assert row["status"] == "sent" and row["resend_id"] == "re_123"
    assert "email.send kind=signin_link status=sent resend_id=re_123" in caplog.text


def test_failed_send_records_the_error(db, monkeypatch):
    monkeypatch.setattr(email_notifications, "RESEND_API_KEY", "re_key")

    def boom(params):
        raise RuntimeError("domain is not verified")
    monkeypatch.setattr(email_notifications.resend.Emails, "send", boom)
    assert run_send() is None
    row = db.email_log.find_one()
    assert row["status"] == "failed" and "not verified" in row["error"]


def test_paced_sender_sends_each_message(db, monkeypatch):
    calls = []

    async def fake_send(to, subject, html, kind="general"):
        calls.append((to, kind))
    monkeypatch.setattr(email_notifications, "send_email", fake_send)

    started = []
    import threading

    class Immediate:
        def __init__(self, target, daemon):
            self.target = target
        def start(self):
            started.append(1)
            self.target()
    monkeypatch.setattr(threading, "Thread", Immediate)
    email_notifications.send_paced_in_background(
        [("a@example.test", "s", "h", "welcome"), ("b@example.test", "s", "h", "welcome")], interval=0)
    assert started == [1] and calls == [("a@example.test", "welcome"), ("b@example.test", "welcome")]


def test_admin_email_log_view(client, db, monkeypatch):
    monkeypatch.setattr(email_notifications, "RESEND_API_KEY", None)
    run_send(kind="welcome")
    assert client.get("/api/notifications/email/log", headers={"X-Session-ID": "s-ada"}).status_code == 403
    body = client.get("/api/notifications/email/log?to=ADA@example.test",
                      headers={"X-Session-ID": "s-admin"}).json()
    assert body["configured"] is False
    assert body["summary"] == {"not_configured": 1}
    assert body["entries"][0]["kind"] == "welcome"
