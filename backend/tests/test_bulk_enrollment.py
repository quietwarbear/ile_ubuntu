"""Roster import (item I1): the service and its routes.

Real code against an in-memory Mongo (mongomock): no server, no database.
"""

from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import bulk_enrollment
import database
import events
import middleware
import tier_gating
from routes import auth, courses, email_notifications, enrollment_imports, subscriptions

NOW = datetime.now(timezone.utc)
MODULES = (database, bulk_enrollment, events, middleware, tier_gating, auth, courses, enrollment_imports,
           subscriptions)


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    for module in (auth, enrollment_imports):
        monkeypatch.setattr(module, "rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(email_notifications, "RESEND_API_KEY", None, raising=False)

    people = {"owner": "faculty", "coteach": "faculty", "otherfaculty": "faculty",
              "student": "student", "admin": "admin"}
    for key, role in people.items():
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test", "subscription_tier": "explorer"})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    for cid, title, vis, extra in (
        ("c-day1", "Day One", "private", {}),
        ("c-day2", "Day Two", "private", {}),
        ("c-paid", "Paid Intensive", "listed", {"is_premium": True, "premium_price": 40}),
        ("c-other", "Someone Else's Course", "private", {"instructor_id": "u-otherfaculty",
                                                        "co_instructor_ids": []}),
    ):
        mdb.courses.insert_one({
            "id": cid, "title": title, "description": "", "status": "active",
            "visibility": vis, "instructor_id": "u-owner", "co_instructor_ids": ["u-coteach"],
            "tags": [], "created_at": NOW, "enrolled_count": 0, **extra,
        })
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    for module in (auth, courses, enrollment_imports, subscriptions):
        app.include_router(module.router)
    return TestClient(app)


def as_(who):
    return {"X-Session-ID": f"s-{who}"}


OWNER = {"id": "u-owner", "role": "faculty"}
MAP = {"Day 1": "c-day1", "Day 2": "c-day2"}


def roster(*lines, header="name,email,sessions"):
    return "\n".join((header,) + lines) + "\n"


def run(db, text, session_map=MAP, actor=OWNER, **kw):
    parsed = bulk_enrollment.parse_roster_csv(text)
    report = bulk_enrollment.import_enrollments(parsed["rows"], session_map, actor, **kw)
    report["parse_errors"] = parsed["errors"]
    return report


def enrolled(db, email):
    user = db.users.find_one({"email": email})
    return sorted(e["course_id"] for e in db.enrollments.find({"user_id": user["id"]}))


# --- parsing ---------------------------------------------------------------------

def test_parse_reads_columns_in_any_order_and_splits_sessions():
    parsed = bulk_enrollment.parse_roster_csv(
        "﻿Sessions,Email,Name\n\"Day 1; Day 2 | Day 1\", Ada@Example.TEST ,Ada Obi\n"
    )
    assert parsed["errors"] == []
    assert parsed["rows"] == [{"row": 2, "name": "Ada Obi", "email": "ada@example.test",
                               "sessions": ["Day 1", "Day 2"]}]


def test_parse_keeps_commas_inside_a_session_label():
    parsed = bulk_enrollment.parse_roster_csv(roster('A,a@example.test,"Saturday, June 6"'))
    assert parsed["rows"][0]["sessions"] == ["Saturday, June 6"]


def test_parse_reports_bad_rows_by_spreadsheet_row_number():
    parsed = bulk_enrollment.parse_roster_csv(roster(
        "Good,good@example.test,Day 1",
        "No email,,Day 1",
        ",,",
        "Bad email,not-an-email,Day 1",
        "No sessions,nosessions@example.test,",
    ))
    assert [r["email"] for r in parsed["rows"]] == ["good@example.test"]
    assert [(e["row"], e["error"]) for e in parsed["errors"]] == [
        (3, "Missing or invalid email"),
        (5, "Missing or invalid email"),
        (6, "No sessions listed"),
    ]


def test_parse_rejects_a_file_without_the_needed_columns():
    with pytest.raises(bulk_enrollment.BulkImportError):
        bulk_enrollment.parse_roster_csv("name,phone\nA,555\n")
    with pytest.raises(bulk_enrollment.BulkImportError):
        bulk_enrollment.parse_roster_csv("")


# --- the service -------------------------------------------------------------------

def test_new_person_gets_an_invited_account_and_exactly_their_sessions(db):
    report = run(db, roster("Ada Obi,ada@example.test,Day 1"))
    assert report["counts"] == {"created": 1, "enrolled": 1, "skipped": 0, "errors": 0}
    user = db.users.find_one({"email": "ada@example.test"})
    assert user["name"] == "Ada Obi"
    assert user["role"] == "student"
    assert user["auth_provider"] == "invited" and user["invited"] is True
    assert "password_hash" not in user
    assert enrolled(db, "ada@example.test") == ["c-day1"]
    enrollment = db.enrollments.find_one({"user_id": user["id"]})
    assert enrollment["source"] == "import" and enrollment["added_by"] == "u-owner"
    assert db.courses.find_one({"id": "c-day1"})["enrolled_count"] == 1


def test_existing_person_is_enrolled_and_their_account_is_left_alone(db):
    before = db.users.find_one({"id": "u-student"}, {"_id": 0})
    report = run(db, roster("A Different Name,student@example.test,Day 1;Day 2"))
    assert report["counts"]["created"] == 0
    assert report["counts"]["enrolled"] == 2
    assert db.users.find_one({"id": "u-student"}, {"_id": 0}) == before
    assert enrolled(db, "student@example.test") == ["c-day1", "c-day2"]


def test_mixed_case_and_spaces_match_one_account(db):
    db.users.insert_one({"id": "u-legacy", "role": "student", "name": "Legacy",
                         "email": "Legacy.Person@Example.test"})
    report = run(db, roster(
        "Ada,  ADA@Example.Test ,Day 1",
        "Ada again,ada@example.test,Day 2",
        "Legacy,legacy.person@example.test,Day 1",
    ))
    assert db.users.count_documents({"email": "ada@example.test"}) == 1
    assert db.users.count_documents({"email": {"$regex": "^legacy", "$options": "i"}}) == 1
    assert report["counts"]["created"] == 1
    assert enrolled(db, "ada@example.test") == ["c-day1", "c-day2"]
    assert db.enrollments.count_documents({"user_id": "u-legacy"}) == 1


def test_rerun_with_added_rows_only_adds_the_new_people_and_courses(db):
    first = roster("Ada,ada@example.test,Day 1", "Bo,bo@example.test,Day 1")
    run(db, first)
    users, enrollments = db.users.count_documents({}), db.enrollments.count_documents({})

    again = run(db, first)
    assert again["counts"] == {"created": 0, "enrolled": 0, "skipped": 2, "errors": 0}
    assert {s["reason"] for s in again["skipped"]} == {"Already enrolled"}
    assert db.users.count_documents({}) == users
    assert db.enrollments.count_documents({}) == enrollments

    grown = run(db, roster("Ada,ada@example.test,Day 1;Day 2", "Bo,bo@example.test,Day 1",
                           "Cy,cy@example.test,Day 2"))
    assert grown["counts"] == {"created": 1, "enrolled": 2, "skipped": 2, "errors": 0}
    assert db.users.count_documents({}) == users + 1
    assert enrolled(db, "ada@example.test") == ["c-day1", "c-day2"]
    assert db.courses.find_one({"id": "c-day1"})["enrolled_count"] == 2
    assert db.courses.find_one({"id": "c-day2"})["enrolled_count"] == 2


def test_same_person_twice_in_one_file_is_not_enrolled_twice(db):
    report = run(db, roster("Ada,ada@example.test,Day 1", "Ada,ADA@example.test,Day 1"))
    assert report["counts"]["enrolled"] == 1
    assert report["skipped"][0]["reason"] == "Listed twice in this file"
    assert db.enrollments.count_documents({}) == 1


def test_row_with_an_unknown_session_is_rejected_whole(db):
    report = run(db, roster("Ada,ada@example.test,Day 1;Day 9", "Bo,bo@example.test,Day 2"))
    assert report["errors"] == [{"row": 2, "email": "ada@example.test",
                                 "error": "Unknown session: Day 9"}]
    assert db.users.find_one({"email": "ada@example.test"}) is None
    assert enrolled(db, "bo@example.test") == ["c-day2"]


def test_a_session_can_name_a_course_id_directly(db):
    report = run(db, roster("Ada,ada@example.test,c-day2"), session_map={})
    assert report["counts"]["enrolled"] == 1
    assert enrolled(db, "ada@example.test") == ["c-day2"]


def test_courses_you_dont_run_are_unknown_even_if_they_exist(db):
    report = run(db, roster("Ada,ada@example.test,c-other"), session_map={})
    assert report["errors"][0]["error"] == "Unknown session: c-other"
    assert db.users.find_one({"email": "ada@example.test"}) is None


def test_platform_faculty_cannot_import_into_a_course_they_dont_teach(db):
    other = {"id": "u-otherfaculty", "role": "faculty"}
    report = run(db, roster("Ada,ada@example.test,Day 1"), actor=other)
    assert report["counts"]["enrolled"] == 0 and report["counts"]["errors"] == 1


def test_co_teacher_and_admin_can_import(db):
    assert run(db, roster("Ada,ada@example.test,Day 1"),
               actor={"id": "u-coteach", "role": "faculty"})["counts"]["enrolled"] == 1
    assert run(db, roster("Bo,bo@example.test,c-other"), session_map={},
               actor={"id": "u-admin", "role": "admin"})["counts"]["enrolled"] == 1


def test_trusted_internal_caller_needs_no_actor(db):
    """X2 (Kindred handoff) calls the service directly after authorizing itself."""
    report = bulk_enrollment.import_enrollments(
        [{"name": "Ada", "email": "Ada@Example.test", "sessions": ["c-other"]}], None, None)
    assert report["counts"] == {"created": 1, "enrolled": 1, "skipped": 0, "errors": 0}


def test_dry_run_writes_nothing_but_reports_the_same(db):
    text = roster("Ada,ada@example.test,Day 1;Day 2", "Ada,ada@example.test,Day 1",
                  "Student,student@example.test,Day 1")
    preview = run(db, text, dry_run=True)
    assert db.users.count_documents({"email": "ada@example.test"}) == 0
    assert db.enrollments.count_documents({}) == 0
    real = run(db, text)
    assert preview["counts"] == real["counts"] == {"created": 1, "enrolled": 3, "skipped": 1, "errors": 0}


def test_imported_enrollments_skip_premium_and_tier_limits(db):
    # An explorer is capped at 2 self-enrollments; three imported ones are fine,
    # including a paid course, and don't use up their own allowance.
    report = run(db, roster("Student,student@example.test,Day 1;Day 2;c-paid"))
    assert report["counts"]["enrolled"] == 3
    tier_gating.check_enrollment_limit(db.users.find_one({"id": "u-student"}))  # no raise


def test_imported_person_still_cannot_self_enroll_in_another_private_course(client, db):
    run(db, roster("Student,student@example.test,Day 1"))
    assert client.post("/api/courses/c-day2/enroll", headers=as_("student")).status_code == 403


def test_imported_student_reaches_their_private_course(client, db):
    run(db, roster("Student,student@example.test,Day 1"))
    assert client.get("/api/courses/c-day1", headers=as_("student")).status_code == 200
    assert client.get("/api/courses/c-day2", headers=as_("student")).status_code == 404


# --- routes --------------------------------------------------------------------------

def test_importable_courses_lists_only_courses_you_run(client):
    ids = {c["id"] for c in client.get("/api/enrollment-imports/courses", headers=as_("coteach")).json()}
    assert ids == {"c-day1", "c-day2", "c-paid"}
    ids = {c["id"] for c in client.get("/api/enrollment-imports/courses", headers=as_("admin")).json()}
    assert "c-other" in ids


def test_preview_suggests_mapping_by_title_and_writes_nothing(client, db):
    text = roster("Ada,ada@example.test,Day One", "Bo,bo@example.test,Mystery day", ",bad,Day One")
    res = client.post("/api/enrollment-imports/preview", headers=as_("owner"),
                      json={"csv": text, "session_map": {}})
    assert res.status_code == 200
    body = res.json()
    assert body["total_rows"] == 3
    assert [r["email"] for r in body["preview_rows"]] == ["ada@example.test", "bo@example.test"]
    assert body["sessions"] == [{"label": "Day One", "course_id": "c-day1"},
                                {"label": "Mystery day", "course_id": None}]
    assert body["report"]["dry_run"] is True
    assert body["report"]["counts"] == {"created": 1, "enrolled": 1, "skipped": 0, "errors": 2}
    assert db.users.count_documents({"email": "ada@example.test"}) == 0


def test_preview_honours_the_organizers_mapping(client):
    text = roster("Bo,bo@example.test,Mystery day")
    body = client.post("/api/enrollment-imports/preview", headers=as_("owner"),
                       json={"csv": text, "session_map": {"Mystery day": "c-day2"}}).json()
    assert body["sessions"] == [{"label": "Mystery day", "course_id": "c-day2"}]
    assert body["report"]["counts"]["enrolled"] == 1


def test_run_import_returns_the_report_with_row_errors(client, db):
    text = roster("Ada,ada@example.test,Day 1", "Nope,,Day 1")
    res = client.post("/api/enrollment-imports", headers=as_("owner"),
                      json={"csv": text, "session_map": MAP})
    assert res.status_code == 200
    body = res.json()
    assert body["counts"] == {"created": 1, "enrolled": 1, "skipped": 0, "errors": 1}
    assert body["errors"][0]["row"] == 3
    assert enrolled(db, "ada@example.test") == ["c-day1"]


def test_bad_file_is_a_400(client):
    res = client.post("/api/enrollment-imports", headers=as_("owner"),
                      json={"csv": "name,phone\nA,1\n", "session_map": {}})
    assert res.status_code == 400 and "email" in res.json()["detail"]
    res = client.post("/api/enrollment-imports", headers=as_("owner"), json={"session_map": {}})
    assert res.status_code == 400


def test_import_needs_sign_in(client):
    assert client.post("/api/enrollment-imports", json={"csv": roster()}).status_code == 401


def test_student_importing_gets_only_errors_and_creates_nothing(client, db):
    res = client.post("/api/enrollment-imports", headers=as_("student"),
                      json={"csv": roster("Ada,ada@example.test,Day 1"), "session_map": MAP})
    assert res.json()["counts"] == {"created": 0, "enrolled": 0, "skipped": 0, "errors": 1}
    assert db.users.find_one({"email": "ada@example.test"}) is None


def test_usage_count_leaves_out_imported_enrollments(client, db):
    run(db, roster("Student,student@example.test,Day 1;Day 2"))
    db.enrollments.insert_one({"user_id": "u-student", "course_id": "c-paid"})  # self-enrolled
    body = client.get("/api/subscriptions/my-subscription", headers=as_("student"))
    assert body.status_code == 200
    assert body.json()["enrollment_count"] == 1


# --- getting in: invited accounts -----------------------------------------------------

def test_invited_person_is_pointed_to_forgot_password(client, db):
    run(db, roster("Ada,ada@example.test,Day 1"))
    login = client.post("/api/auth/login", json={"email": "ada@example.test", "password": "whatever"})
    assert login.status_code == 401 and "Forgot password" in login.json()["detail"]
    reg = client.post("/api/auth/register", json={"email": "ada@example.test", "password": "secret123"})
    assert reg.status_code == 409 and "Forgot password" in reg.json()["detail"]
    assert "password_hash" not in db.users.find_one({"email": "ada@example.test"})


def test_invited_person_sets_a_password_through_the_reset_email(client, db, monkeypatch):
    run(db, roster("Ada,ada@example.test,Day 1"))
    sent = []

    async def fake_send(to, subject, html):
        sent.append(html)
    monkeypatch.setattr(email_notifications, "send_email", fake_send)

    assert client.post("/api/auth/forgot-password", json={"email": "ada@example.test"}).status_code == 200
    assert db.password_resets.count_documents({}) == 1 and sent
    token = sent[0].split("reset-password?token=")[1].split('"')[0]
    res = client.post("/api/auth/reset-password", json={"token": token, "password": "secret123"})
    assert res.status_code == 200
    user = db.users.find_one({"email": "ada@example.test"})
    assert user["auth_provider"] == "password" and user["password_hash"]
    login = client.post("/api/auth/login", json={"email": "ada@example.test", "password": "secret123"})
    assert login.status_code == 200
