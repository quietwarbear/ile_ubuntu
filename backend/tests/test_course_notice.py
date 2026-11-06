"""Course notice (item I7). Real routes on an in-memory Mongo (mongomock)."""

from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import database
import middleware
from routes import course_notice, courses, villages

NOW = datetime.now(timezone.utc)
MODULES = (database, middleware, courses, course_notice, villages)


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    for key, role in (("owner", "faculty"), ("coteacher", "faculty"), ("student", "student"),
                      ("outsider", "student"), ("faculty", "faculty"), ("admin", "admin")):
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test"})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})
    mdb.courses.insert_one({"id": "c1", "title": "Weekend sessions", "instructor_id": "u-owner",
                            "co_instructor_ids": ["u-coteacher"], "status": "active",
                            "visibility": "listed"})
    mdb.enrollments.insert_one({"id": "e1", "user_id": "u-student", "course_id": "c1"})
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(courses.router)
    app.include_router(course_notice.router)
    return TestClient(app)


def as_(who):
    return {"X-Session-ID": f"s-{who}"}


URL = "/api/courses/c1/notice"
TEXT = "## Sharing\nRecordings are for enrolled participants only.\n\n**Credits:** our hosts."


def test_no_notice_by_default(client):
    assert client.get(URL, headers=as_("student")).status_code == 404


def test_staff_write_and_enrolled_students_read(client):
    res = client.put(URL, headers=as_("owner"), json={"body": TEXT})
    assert res.status_code == 200
    for who in ("student", "owner", "coteacher", "admin"):
        got = client.get(URL, headers=as_(who))
        assert got.status_code == 200, who
        assert got.json()["body"] == TEXT


def test_outsiders_cannot_read_it_or_tell_it_exists(client):
    client.put(URL, headers=as_("owner"), json={"body": TEXT})
    for who in ("outsider", "faculty"):            # platform faculty isn't this course's staff
        res = client.get(URL, headers=as_(who))
        assert res.status_code == 404 and res.json()["detail"] == "No notice"
    assert client.get(URL).status_code in (401, 403)  # signed out


def test_only_course_staff_can_edit(client):
    assert client.put(URL, headers=as_("coteacher"), json={"body": TEXT}).status_code == 200
    for who in ("student", "outsider", "faculty"):
        assert client.put(URL, headers=as_(who), json={"body": "mine now"}).status_code == 403


def test_clearing_removes_it(client, db):
    client.put(URL, headers=as_("owner"), json={"body": TEXT})
    assert client.put(URL, headers=as_("owner"), json={"body": "   "}).status_code == 200
    assert db.course_notices.count_documents({}) == 0
    assert client.get(URL, headers=as_("student")).status_code == 404


def test_validation(client):
    assert client.put(URL, headers=as_("owner"), json={"body": 5}).status_code == 400
    too_long = "x" * (course_notice.MAX_NOTICE_CHARS + 1)
    assert client.put(URL, headers=as_("owner"), json={"body": too_long}).status_code == 400
    assert client.put("/api/courses/nope/notice", headers=as_("owner"), json={"body": "x"}).status_code == 404


def test_never_rides_on_course_documents(client):
    client.put(URL, headers=as_("owner"), json={"body": TEXT})
    for who in ("outsider", "student"):
        body = client.get("/api/courses/c1", headers=as_(who)).json()
        assert "notice" not in body and TEXT not in str(body)
    listing = client.get("/api/courses", headers=as_("outsider"))
    assert TEXT not in listing.text
