"""Lesson release scheduling and course-staff rules.

These decide whether unreleased material reaches a student, so they are pinned
directly against the committed source. The functions are extracted from
routes/courses.py and executed in a bare namespace — the module itself needs
FastAPI and a live Mongo, which no unit test should require.
"""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

COURSES = Path(__file__).resolve().parents[1] / "routes" / "courses.py"
SOURCE = COURSES.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

WANTED_FUNCS = (
    "_as_utc",
    "_lesson_is_open",
    "_locked_lesson_stub",
    "_course_staff_ids",
    "_is_course_staff",
)
WANTED_NAMES = ("_LOCKED_LESSON_FIELDS", "MAX_CO_INSTRUCTORS")


class _Role:
    ADMIN = "admin"
    STUDENT = "student"


def _load():
    body = []
    for node in TREE.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in WANTED_FUNCS:
            body.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in WANTED_NAMES for t in node.targets
        ):
            body.append(node)
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    ns = {"datetime": datetime, "timezone": timezone, "UserRole": _Role}
    exec(compile(module, str(COURSES), "exec"), ns)
    missing = [n for n in WANTED_FUNCS + WANTED_NAMES if n not in ns]
    assert not missing, f"not found in courses.py: {missing}"
    return ns


NS = _load()
as_utc = NS["_as_utc"]
is_open = NS["_lesson_is_open"]
locked_stub = NS["_locked_lesson_stub"]
is_course_staff = NS["_is_course_staff"]

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
PAST = NOW - timedelta(hours=1)
FUTURE = NOW + timedelta(hours=1)


# --- timestamp normalisation -------------------------------------------------

@pytest.mark.parametrize(
    "value",
    ["2026-09-05T12:00:00Z", "2026-09-05T12:00:00+00:00", datetime(2026, 9, 5, 12, 0)],
)
def test_as_utc_normalises_to_aware_utc(value):
    """Mongo returns naive datetimes; the API accepts ISO strings. Both must
    end up comparable, or every comparison raises."""
    got = as_utc(value)
    assert got is not None and got.tzinfo is not None
    assert got == NOW


@pytest.mark.parametrize("value", ["not a date", "", None, 12345, "2026-13-45T99:00:00Z"])
def test_as_utc_rejects_junk(value):
    assert as_utc(value) is None


# --- release rules -----------------------------------------------------------

def test_lesson_with_no_schedule_is_open():
    assert is_open({"title": "Week 1"}, NOW) is True


def test_hidden_lesson_is_closed_even_when_scheduled_in_the_past():
    """Manual hide always wins — that is the teacher's emergency brake."""
    assert is_open({"hidden": True, "available_at": PAST}, NOW) is False


def test_scheduled_lesson_is_closed_before_its_moment():
    assert is_open({"available_at": FUTURE}, NOW) is False


def test_scheduled_lesson_opens_once_the_moment_passes():
    assert is_open({"available_at": PAST}, NOW) is True


def test_release_is_inclusive_of_the_exact_moment():
    assert is_open({"available_at": NOW}, NOW) is True


def test_naive_stored_timestamp_is_treated_as_utc():
    """Mongo strips tzinfo on the way back out. Without normalisation this
    comparison raises and the lesson's state becomes an exception."""
    assert is_open({"available_at": datetime(2026, 9, 5, 11, 0)}, NOW) is True


def test_unparseable_schedule_fails_closed():
    """A corrupt timestamp must withhold the lesson, never publish it."""
    assert is_open({"available_at": "sometime next week"}, NOW) is False


# --- what a student sees of an unreleased lesson ------------------------------

def test_locked_stub_carries_no_teaching_content():
    lesson = {
        "id": "l1",
        "course_id": "c1",
        "title": "Week 3",
        "order": 3,
        "module_id": "m1",
        "available_at": FUTURE,
        "content": "SECRET",
        "description": "SECRET",
        "video_url": "https://secret",
        "video_file_id": "f1",
        "banner_url": "https://secret",
        "files": ["f1"],
    }
    stub = locked_stub(lesson)
    assert stub["locked"] is True
    assert stub["title"] == "Week 3" and stub["available_at"] == FUTURE
    for leaked in ("content", "description", "video_url", "video_file_id", "banner_url", "files"):
        assert leaked not in stub, f"{leaked} leaked into the locked stub"


# --- course staff ------------------------------------------------------------

OWNER = {"id": "owner", "role": _Role.STUDENT}
CO = {"id": "co", "role": _Role.STUDENT}
STRANGER = {"id": "stranger", "role": _Role.STUDENT}
ADMIN = {"id": "admin", "role": _Role.ADMIN}
COURSE = {"instructor_id": "owner", "co_instructor_ids": ["co"]}


@pytest.mark.parametrize("user", [OWNER, CO, ADMIN])
def test_staff_recognised(user):
    assert is_course_staff(COURSE, user) is True


def test_stranger_is_not_staff():
    assert is_course_staff(COURSE, STRANGER) is False


def test_course_without_the_field_still_works():
    """Courses created before co-teaching existed have no co_instructor_ids."""
    legacy = {"instructor_id": "owner"}
    assert is_course_staff(legacy, OWNER) is True
    assert is_course_staff(legacy, CO) is False


def test_co_teacher_cap_is_two():
    assert NS["MAX_CO_INSTRUCTORS"] == 2
