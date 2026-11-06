"""Private courses, lesson reads, and the certificates switch (item I2).

Real routes against an in-memory Mongo (mongomock): no server, no database.
Every *_col a module imported is swapped for the same mongomock collection.
"""

from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection

import middleware
from routes import certificates, courses, discussions, marketplace, search, villages

NOW = datetime.now(timezone.utc)
MODULES = (middleware, courses, certificates, discussions, marketplace, search, villages)


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient().db
    for module in MODULES:
        for name, value in list(vars(module).items()):
            if name.endswith("_col") and isinstance(value, Collection):
                monkeypatch.setattr(module, name, mdb[value.name])
    monkeypatch.setattr(courses, "emit", lambda *a, **k: None)
    monkeypatch.setattr(courses, "check_enrollment_limit", lambda user: None)

    people = {
        "owner": "faculty", "coteach": "faculty", "otherfaculty": "faculty",
        "assistant": "assistant", "student": "student", "outsider": "student", "admin": "admin",
    }
    for key, role in people.items():
        mdb.users.insert_one({"id": f"u-{key}", "role": role, "name": key.title(),
                              "email": f"{key}@example.test"})
        mdb.sessions.insert_one({"session_id": f"s-{key}", "user_id": f"u-{key}",
                                 "expires_at": NOW + timedelta(days=1)})

    for cid, vis in (("c-private", "private"), ("c-listed", "listed"), ("c-unlisted", "unlisted")):
        mdb.courses.insert_one({
            "id": cid, "title": f"Ancestral songs {vis}", "description": "A gathering",
            "instructor_id": "u-owner", "co_instructor_ids": ["u-coteach"],
            "status": "active", "visibility": vis, "tags": [], "created_at": NOW,
        })
        mdb.lessons.insert_one({"id": f"l-{cid}", "course_id": cid, "title": "Day one",
                                "order": 1, "content": "the teaching itself"})
        mdb.enrollments.insert_one({"user_id": "u-student", "course_id": cid, "progress": 100,
                                    "completed_at": NOW})
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    for module in (courses, certificates, discussions, marketplace, search):
        app.include_router(module.router)
    return TestClient(app)


def as_(who):
    return {"X-Session-ID": f"s-{who}"}


# --- hidden from catalog and search ----------------------------------------------

def test_private_course_is_not_in_the_catalog(client):
    ids = {c["id"] for c in client.get("/api/courses", headers=as_("outsider")).json()}
    assert "c-private" not in ids and "c-listed" in ids


def test_private_course_is_not_in_other_faculty_catalog(client):
    ids = {c["id"] for c in client.get("/api/courses", headers=as_("otherfaculty")).json()}
    assert "c-private" not in ids


def test_owner_still_sees_their_private_course(client):
    ids = {c["id"] for c in client.get("/api/courses", headers=as_("owner")).json()}
    assert "c-private" in ids


@pytest.mark.parametrize("who", ["outsider", "otherfaculty", "student"])
def test_private_course_never_appears_in_search(client, who):
    found = client.get("/api/search?q=Ancestral", headers=as_(who)).json()["courses"]
    assert "c-private" not in {c["id"] for c in found}
    assert "c-listed" in {c["id"] for c in found}


def test_teachers_find_their_private_course_in_search(client):
    found = client.get("/api/search?q=Ancestral", headers=as_("coteach")).json()["courses"]
    assert "c-private" in {c["id"] for c in found}


# --- 404 for outsiders, open for the class --------------------------------------

@pytest.mark.parametrize("who", ["outsider", "otherfaculty", "assistant"])
def test_outsiders_get_404_for_a_private_course_and_its_lessons(client, who):
    assert client.get("/api/courses/c-private", headers=as_(who)).status_code == 404
    assert client.get("/api/courses/c-private/lessons", headers=as_(who)).status_code == 404


@pytest.mark.parametrize("who", ["student", "owner", "coteach", "admin"])
def test_class_and_staff_open_a_private_course(client, who):
    assert client.get("/api/courses/c-private", headers=as_(who)).status_code == 200
    lessons = client.get("/api/courses/c-private/lessons", headers=as_(who)).json()
    assert lessons[0]["content"] == "the teaching itself"


def test_platform_faculty_cannot_reach_private_discussions(client):
    assert client.get("/api/courses/c-private/discussion/topics", headers=as_("otherfaculty")).status_code == 403


# --- lesson content is for the class on every course ------------------------------

@pytest.mark.parametrize("course_id", ["c-listed", "c-unlisted"])
def test_not_enrolled_sees_the_outline_but_no_content(client, course_id):
    res = client.get(f"/api/courses/{course_id}/lessons", headers=as_("outsider"))
    assert res.status_code == 200
    lesson = res.json()[0]
    assert lesson["title"] == "Day one"
    assert lesson["enrollment_required"] is True and lesson["locked"] is True
    assert "content" not in lesson


def test_enrolled_student_reads_listed_lessons(client):
    lesson = client.get("/api/courses/c-listed/lessons", headers=as_("student")).json()[0]
    assert lesson["content"] == "the teaching itself"


def test_platform_assistant_keeps_reach_on_non_private_courses(client):
    lesson = client.get("/api/courses/c-listed/lessons", headers=as_("assistant")).json()[0]
    assert lesson["content"] == "the teaching itself"


# --- joining ---------------------------------------------------------------------

def test_self_enrollment_in_private_is_rejected(client):
    assert client.post("/api/courses/c-private/enroll", headers=as_("outsider")).status_code == 403


def test_private_course_cannot_be_bought(client, monkeypatch):
    monkeypatch.setattr(marketplace, "MARKETPLACE_KEY", "sk_test_placeholder")  # never called
    res = client.post("/api/marketplace/courses/c-private/checkout", json={}, headers=as_("outsider"))
    assert res.status_code == 404


def test_invite_codes_are_refused_and_switched_off(client, db):
    assert client.post("/api/courses/c-private/invite-code", headers=as_("owner")).status_code == 400

    code = client.post("/api/courses/c-unlisted/invite-code", headers=as_("owner")).json()["code"]
    assert client.get(f"/api/courses/invites/{code}/resolve").status_code == 200
    assert client.post("/api/courses/c-unlisted/visibility", json={"visibility": "private"},
                       headers=as_("owner")).status_code == 200
    assert client.get(f"/api/courses/invites/{code}/resolve").status_code == 404
    assert client.post(f"/api/courses/invites/{code}/accept", headers=as_("outsider")).status_code == 404


def test_invite_for_a_course_made_private_later_is_dead_even_if_still_active(client, db):
    db.course_invites.insert_one({"code": "OLDCODE1", "course_id": "c-private", "active": True})
    assert client.get("/api/courses/invites/OLDCODE1/resolve").status_code == 404
    assert client.post("/api/courses/invites/OLDCODE1/accept", headers=as_("outsider")).status_code == 404


def test_staff_can_still_enroll_someone_in_private(client, db):
    res = client.post("/api/courses/c-private/enrollments", json={"email": "outsider@example.test"},
                      headers=as_("owner"))
    assert res.status_code in (200, 201), res.text
    assert db.enrollments.find_one({"user_id": "u-outsider", "course_id": "c-private"})
    assert client.get("/api/courses/c-private", headers=as_("outsider")).status_code == 200


def test_visibility_value_is_validated(client):
    res = client.post("/api/courses/c-listed/visibility", json={"visibility": "secret"}, headers=as_("owner"))
    assert res.status_code == 400


# --- certificates switch ---------------------------------------------------------

def test_certificates_on_by_default(client):
    assert client.get("/api/certificates/check/c-listed", headers=as_("student")).json()["eligible"] is True


def test_certificates_can_be_turned_off(client):
    assert client.put("/api/courses/c-listed", json={"certificates_enabled": False},
                      headers=as_("owner")).status_code == 200
    check = client.get("/api/certificates/check/c-listed", headers=as_("student")).json()
    assert check["eligible"] is False and check["certificates_enabled"] is False
    assert client.get("/api/certificates/download/c-listed", headers=as_("student")).status_code == 403
    mine = client.get("/api/certificates/my-certificates", headers=as_("student")).json()
    assert "c-listed" not in {c["course_id"] for c in mine}


def test_certificates_flag_must_be_boolean(client):
    res = client.put("/api/courses/c-listed", json={"certificates_enabled": "no"}, headers=as_("owner"))
    assert res.status_code == 400
