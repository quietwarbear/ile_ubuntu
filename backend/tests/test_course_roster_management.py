import asyncio
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException

from routes import courses


class FakeRequest:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


class FakeCourses:
    def __init__(self, course):
        self.course = course

    def find_one(self, query, projection=None):
        return self.course if query.get("id") == self.course["id"] else None

    def update_one(self, query, update):
        if "$inc" in update:
            self.course["enrolled_count"] += update["$inc"]["enrolled_count"]
        if "$set" in update:
            self.course.update(update["$set"])


class FakeUsers:
    def __init__(self, users):
        self.users = users

    def find_one(self, query, projection=None):
        return next((u.copy() for u in self.users if u.get("email") == query.get("email")), None)


class FakeEnrollments:
    def __init__(self, records=None):
        self.records = list(records or [])

    def find_one(self, query, projection=None):
        return next((r for r in self.records if all(r.get(k) == v for k, v in query.items())), None)

    def insert_one(self, record):
        stored = record.copy()
        stored["_id"] = "mongo-id"
        self.records.append(stored)

    def delete_one(self, query):
        found = self.find_one(query)
        if not found:
            return SimpleNamespace(deleted_count=0)
        self.records.remove(found)
        return SimpleNamespace(deleted_count=1)

    def count_documents(self, query):
        return sum(all(r.get(k) == v for k, v in query.items()) for r in self.records)


@pytest.fixture
def roster(monkeypatch):
    course = {
        "id": "course-1", "title": "History", "instructor_id": "owner",
        "co_instructor_ids": ["co-teacher"], "enrolled_count": 0,
    }
    student = {"id": "student-1", "name": "Student One", "email": "student@example.com"}
    fake_courses = FakeCourses(course)
    fake_users = FakeUsers([student])
    fake_enrollments = FakeEnrollments()
    events = []
    monkeypatch.setattr(courses, "courses_col", fake_courses)
    monkeypatch.setattr(courses, "users_col", fake_users)
    monkeypatch.setattr(courses, "enrollments_col", fake_enrollments)
    monkeypatch.setattr(courses, "emit", lambda *args, **kwargs: events.append((args, kwargs)))

    email_module = ModuleType("routes.email_notifications")
    email_module.send_enrollment_email = lambda *args: None
    email_module.send_in_background = lambda *args: None
    monkeypatch.setitem(sys.modules, "routes.email_notifications", email_module)
    return course, fake_enrollments, events


def test_co_teacher_can_add_and_remove_an_existing_student(roster):
    course, enrollments, events = roster
    teacher = {"id": "co-teacher", "name": "Iya", "role": "faculty"}

    added = asyncio.run(courses.add_course_enrollment(
        "course-1", FakeRequest({"email": " STUDENT@example.com "}), teacher,
    ))
    assert added["user_id"] == "student-1"
    assert added["user_email"] == "student@example.com"
    assert course["enrolled_count"] == 1

    removed = courses.remove_course_enrollment("course-1", "student-1", teacher)
    assert removed == {"success": True}
    assert enrollments.records == []
    assert course["enrolled_count"] == 0
    assert [event[0][0] for event in events] == ["course.enrolled", "course.unenrolled"]


def test_unassigned_faculty_cannot_manage_another_course(roster):
    stranger = {"id": "other-faculty", "name": "Other", "role": "faculty"}
    with pytest.raises(HTTPException) as error:
        asyncio.run(courses.add_course_enrollment(
            "course-1", FakeRequest({"email": "student@example.com"}), stranger,
        ))
    assert error.value.status_code == 403


def test_duplicate_roster_entry_is_rejected(roster):
    _, enrollments, _ = roster
    enrollments.records.append({"id": "existing", "user_id": "student-1", "course_id": "course-1"})
    owner = {"id": "owner", "name": "Owner", "role": "faculty"}
    with pytest.raises(HTTPException) as error:
        asyncio.run(courses.add_course_enrollment(
            "course-1", FakeRequest({"email": "student@example.com"}), owner,
        ))
    assert error.value.status_code == 409
