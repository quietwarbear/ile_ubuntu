"""Course access end dates (item I6).

Real routes against an in-memory Mongo (mongomock): no server, no database.
"""

from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import bulk_enrollment
import course_access
import database
import email_signin
import events
import file_access
import middleware
from routes import (courses, discussions, email_notifications, enrollments, files,
                    lesson_comments, marketplace, quizzes, submissions, villages)

NOW = datetime.now(timezone.utc)
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=30)
MODULES = (database, bulk_enrollment, course_access, email_signin, events, file_access, middleware,
           courses, discussions, email_notifications, enrollments, files, lesson_comments,
           marketplace, quizzes, submissions, villages)


@pytest.fixture
def db(monkeypatch, tmp_path):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    monkeypatch.setattr(courses, "emit", lambda *a, **k: None)
    monkeypatch.setattr(courses, "check_enrollment_limit", lambda user: None)
    monkeypatch.setattr(email_notifications, "send_paced_in_background", lambda m: None)

    for key, role in (("owner", "faculty"), ("student", "student"), ("other", "student"),
                      ("newbie", "student")):
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test"})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    mdb.courses.insert_one({"id": "c1", "title": "Weekend sessions", "instructor_id": "u-owner",
                            "co_instructor_ids": [], "status": "active", "visibility": "listed",
                            "access_ends_at": PAST})
    mdb.lessons.insert_one({"id": "l1", "course_id": "c1", "title": "Day one", "order": 1,
                            "content": "the recording", "video_file_id": "f-video"})
    for uid in ("u-student", "u-other"):
        mdb.enrollments.insert_one({"id": f"e-{uid}", "user_id": uid, "course_id": "c1",
                                    "completed_lessons": [], "progress": 0})
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    mdb.files.insert_one({"id": "f-video", "lesson_id": "l1", "course_id": "c1",
                          "uploaded_by": "u-owner", "mime_type": "video/mp4",
                          "file_category": "video", "original_filename": "talk.mp4",
                          "file_path": str(video), "storage": "local"})
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    for module in (courses, files, enrollments, quizzes, lesson_comments, discussions, submissions):
        app.include_router(module.router)
    return TestClient(app, follow_redirects=False)


def as_(who, **extra):
    return {"X-Session-ID": f"s-{who}", **extra}


def set_course_end(db, when):
    db.courses.update_one({"id": "c1"}, {"$set": {"access_ends_at": when}})


# --- the rule ------------------------------------------------------------------------

def test_forever_is_the_default():
    assert course_access.ended_at({"id": "c"}, {"user_id": "u"}) is None


def test_enrollment_follows_the_course_unless_overridden():
    course = {"access_ends_at": PAST}
    assert course_access.ended_at(course, {}) is not None
    assert course_access.ended_at(course, {"access_ends_at": None}) is None        # forever
    assert course_access.ended_at(course, {"access_ends_at": FUTURE}) is None
    assert course_access.ended_at({"access_ends_at": None}, {"access_ends_at": PAST}) is not None


def test_naive_mongo_datetimes_and_unreadable_values():
    naive = (NOW - timedelta(hours=1)).replace(tzinfo=None)
    assert course_access.ended_at({"access_ends_at": naive}, None) is not None
    assert course_access.ended_at({"access_ends_at": "garbage"}, None) is not None   # fail closed


def test_parse_end_accepts_dates_and_rejects_junk():
    end = course_access.parse_end("2026-12-31")
    assert (end.year, end.month, end.day, end.hour, end.minute) == (2026, 12, 31, 23, 59)
    assert course_access.parse_end("2026-12-31T18:00:00Z").hour == 18
    assert course_access.parse_end(None) is None
    with pytest.raises(ValueError):
        course_access.parse_end("next tuesday")
    with pytest.raises(ValueError):
        course_access.parse_end(5)


# --- enforcement ---------------------------------------------------------------------

def test_lessons_refuse_after_the_end(client):
    res = client.get("/api/courses/c1/lessons", headers=as_("student"))
    assert res.status_code == 403 and res.json()["detail"].startswith("access_ended:")


def test_lessons_open_before_the_end(client, db):
    set_course_end(db, FUTURE)
    res = client.get("/api/courses/c1/lessons", headers=as_("student"))
    assert res.status_code == 200 and res.json()[0]["content"] == "the recording"


def test_staff_are_never_affected(client):
    assert client.get("/api/courses/c1/lessons", headers=as_("owner")).status_code == 200
    assert client.get("/api/courses/c1/lessons?view_as_student=true",
                      headers=as_("owner")).status_code == 200
    assert client.get("/api/files/f-video/stream", headers=as_("owner")).status_code == 200


def test_course_page_stays_open_and_says_access_ended(client):
    body = client.get("/api/courses/c1", headers=as_("student")).json()
    assert body["viewer_access"]["access_ended"] is True
    assert body["viewer_access"]["access_ends_at"].startswith(PAST.date().isoformat())


def test_stream_and_download_refuse_with_a_clear_page_or_code(client):
    api = client.get("/api/files/f-video/stream", headers=as_("student"))
    assert api.status_code == 403 and api.json()["detail"].startswith("access_ended:")
    page = client.get("/api/files/f-video/download", headers=as_("student", accept="text/html"))
    assert page.status_code == 403 and "Your access has ended" in page.text


def test_playback_token_endpoint_withholds_and_explains(client):
    body = client.post("/api/files/access-tokens", headers=as_("student"),
                       json={"file_ids": ["f-video"]}).json()
    assert body["tokens"] == {}
    assert body["ended"]["f-video"].startswith("access_ended:")


def test_a_token_issued_before_the_end_stops_working_after_it(client, db):
    set_course_end(db, FUTURE)
    token = client.post("/api/files/access-tokens", headers=as_("student"),
                        json={"file_ids": ["f-video"]}).json()["tokens"]["f-video"]["token"]
    assert client.get(f"/api/files/f-video/stream?t={token}").status_code == 200
    set_course_end(db, PAST)
    assert client.get(f"/api/files/f-video/stream?t={token}").status_code == 403


def test_completing_lessons_quizzes_comments_discussions_submissions_refuse(client, db):
    db.quizzes.insert_one({"id": "q1", "lesson_id": "l1", "course_id": "c1", "questions": []})
    checks = [
        client.post("/api/courses/c1/lessons/l1/complete", headers=as_("student")),
        client.post("/api/courses/c1/lessons/l1/quiz/submit", headers=as_("student"), json={"answers": {}}),
        client.get("/api/courses/c1/lessons/l1/comments", headers=as_("student")),
        client.get("/api/courses/c1/discussion/topics", headers=as_("student")),
        client.get("/api/courses/c1/lessons/l1/submissions/mine", headers=as_("student")),
    ]
    codes = [(r.request.url.path, r.status_code, r.json().get("detail", "")) for r in checks]
    for path, code, detail in codes:
        assert code == 403 and str(detail).startswith("access_ended:"), (path, code, detail)


def test_cannot_join_a_course_whose_access_period_is_over(client):
    res = client.post("/api/courses/c1/enroll", headers=as_("newbie"))
    assert res.status_code == 400 and "ended" in res.json()["detail"]


# --- staff override ------------------------------------------------------------------

def test_staff_can_extend_one_person_and_reset_them(client, db):
    url = "/api/courses/c1/enrollments/u-student/access"
    res = client.put(url, headers=as_("owner"), json={"access_ends_at": FUTURE.isoformat()})
    assert res.status_code == 200 and res.json()["overridden"] is True
    assert client.get("/api/courses/c1/lessons", headers=as_("student")).status_code == 200
    assert client.get("/api/courses/c1/lessons", headers=as_("other")).status_code == 403

    client.put(url, headers=as_("owner"), json={"access_ends_at": None})        # forever
    assert db.enrollments.find_one({"user_id": "u-student"})["access_ends_at"] is None
    assert client.get("/api/courses/c1/lessons", headers=as_("student")).status_code == 200

    client.put(url, headers=as_("owner"), json={"inherit": True})
    assert "access_ends_at" not in db.enrollments.find_one({"user_id": "u-student"})
    assert client.get("/api/courses/c1/lessons", headers=as_("student")).status_code == 403


def test_override_needs_staff_and_valid_input(client):
    url = "/api/courses/c1/enrollments/u-student/access"
    assert client.put(url, headers=as_("student"), json={"access_ends_at": None}).status_code == 403
    assert client.put(url, headers=as_("owner"), json={"access_ends_at": "soon"}).status_code == 400
    assert client.put(url, headers=as_("owner"), json={}).status_code == 400
    assert client.put("/api/courses/c1/enrollments/u-nobody/access", headers=as_("owner"),
                      json={"inherit": True}).status_code == 404


def test_roster_shows_each_persons_access(client, db):
    db.enrollments.update_one({"user_id": "u-student"}, {"$set": {"access_ends_at": FUTURE}})
    rows = {r["user_id"]: r for r in client.get("/api/courses/c1/enrollments", headers=as_("owner")).json()}
    assert rows["u-student"]["access_ended"] is False and rows["u-student"]["overridden"] is True
    assert rows["u-other"]["access_ended"] is True and rows["u-other"]["overridden"] is False


def test_my_courses_shows_the_end(client):
    rows = client.get("/api/enrollments/my-courses", headers=as_("student")).json()
    assert rows[0]["access_ended"] is True


# --- setting it on the course ---------------------------------------------------------

def test_owner_sets_and_clears_the_course_end(client, db):
    res = client.put("/api/courses/c1", headers=as_("owner"), json={"access_ends_at": "2030-01-31"})
    assert res.status_code == 200
    assert client.get("/api/courses/c1/lessons", headers=as_("student")).status_code == 200
    client.put("/api/courses/c1", headers=as_("owner"), json={"access_ends_at": None})
    assert db.courses.find_one({"id": "c1"})["access_ends_at"] is None
    assert client.put("/api/courses/c1", headers=as_("owner"),
                      json={"access_ends_at": "whenever"}).status_code == 400


# --- I1 import inherits ---------------------------------------------------------------

def test_imported_enrollments_follow_the_course_setting(client, db):
    set_course_end(db, FUTURE)
    bulk_enrollment.import_enrollments(
        [{"name": "Newbie", "email": "newbie@example.test", "sessions": ["c1"]}], {},
        {"id": "u-owner", "role": "faculty"})
    enrollment = db.enrollments.find_one({"user_id": "u-newbie"})
    assert "access_ends_at" not in enrollment        # inherits, live
    assert client.get("/api/courses/c1/lessons", headers=as_("newbie")).status_code == 200
    set_course_end(db, PAST)                           # organizer moves the date
    assert client.get("/api/courses/c1/lessons", headers=as_("newbie")).status_code == 403


def test_staff_can_still_import_into_an_ended_course_and_override(client, db):
    report = bulk_enrollment.import_enrollments(
        [{"email": "newbie@example.test", "sessions": ["c1"]}], {}, {"id": "u-owner", "role": "faculty"})
    assert report["counts"]["enrolled"] == 1
    client.put("/api/courses/c1/enrollments/u-newbie/access", headers=as_("owner"),
               json={"access_ends_at": FUTURE.isoformat()})
    assert client.get("/api/courses/c1/lessons", headers=as_("newbie")).status_code == 200
