"""Who gets told, at which address, and what reaches the HTML.

Getting this wrong is quiet in both directions: too eager and it spams the
teaching team, too shy and a student's work sits unseen. Pinned against the
committed source, executed with a stub collection.
"""

import ast
from html import escape
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "teacher_alerts.py"
SOURCE = SRC.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

WANTED = ("_staff_ids", "recipients", "_excerpt")
NAMES = ("PREF_FIELD", "EXCERPT_CHARS")


class StubUsers:
    """Stands in for users_col.find({'id': {'$in': [...]}}, projection)."""

    def __init__(self, docs):
        self.docs = docs

    def find(self, query, _projection=None):
        wanted = query["id"]["$in"]
        return [d for d in self.docs if d["id"] in wanted]


def load(docs):
    body = [
        n for n in TREE.body
        if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in WANTED)
        or (isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in NAMES for t in n.targets))
    ]
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    ns = {"users_col": StubUsers(docs), "esc": escape}
    exec(compile(module, str(SRC), "exec"), ns)
    return ns


COURSE = {"id": "c1", "instructor_id": "shy", "co_instructor_ids": ["yeye"]}

TEAM = [
    {"id": "shy", "name": "Shy", "email": "shy@account.test"},
    {"id": "yeye", "name": "Yeye", "email": "yeye@account.test"},
]


def emails(docs, kind="submission", exclude=None, course=COURSE):
    ns = load(docs)
    return sorted(p["email"] for p in ns["recipients"](course, kind, exclude_id=exclude))


def test_both_teachers_are_told_by_default():
    """No preference set means alerts on — a teacher who never opened the
    setting still hears when work is handed in."""
    assert emails(TEAM) == ["shy@account.test", "yeye@account.test"]


def test_the_person_who_acted_is_never_emailed():
    assert emails(TEAM, exclude="shy") == ["yeye@account.test"]


def test_a_preferred_address_wins_over_the_account_one():
    docs = [dict(TEAM[0], notification_email="shy@preferred.test"), TEAM[1]]
    assert emails(docs) == ["shy@preferred.test", "yeye@account.test"]


def test_a_blank_preferred_address_falls_back_to_the_account():
    docs = [dict(TEAM[0], notification_email="   "), TEAM[1]]
    assert emails(docs) == ["shy@account.test", "yeye@account.test"]


def test_opting_out_is_respected_per_kind():
    docs = [dict(TEAM[0], notify_submissions=False), TEAM[1]]
    assert emails(docs, kind="submission") == ["yeye@account.test"]
    # Opting out of one kind must not silence the other.
    assert emails(docs, kind="discussion") == ["shy@account.test", "yeye@account.test"]


def test_a_teacher_with_no_address_is_skipped_not_crashed():
    docs = [dict(TEAM[0], email=""), TEAM[1]]
    assert emails(docs) == ["yeye@account.test"]


def test_students_are_not_course_staff():
    docs = TEAM + [{"id": "student", "name": "S", "email": "student@test"}]
    assert "student@test" not in emails(docs)


def test_a_course_with_no_co_teachers_still_notifies_the_owner():
    solo = {"id": "c2", "instructor_id": "shy"}
    assert emails(TEAM, course=solo) == ["shy@account.test"]


def test_excerpt_escapes_student_text():
    """A topic title or reply is student input and lands in an HTML email."""
    ns = load(TEAM)
    out = ns["_excerpt"]('<img src=x onerror="alert(1)">')
    assert "<img" not in out
    assert "&lt;img" in out


def test_excerpt_is_truncated_and_keeps_line_breaks():
    ns = load(TEAM)
    limit = ns["EXCERPT_CHARS"]
    long_text = "x" * (limit + 50)
    out = ns["_excerpt"](long_text)
    assert out.endswith("…") and len(out) <= limit + 1
    assert ns["_excerpt"]("one\ntwo") == "one<br>two"


@pytest.mark.parametrize("kind", ["discussion", "submission"])
def test_both_alert_kinds_have_a_switch(kind):
    ns = load(TEAM)
    assert kind in ns["PREF_FIELD"]


def test_a_mail_failure_never_breaks_the_student_action():
    """_send swallows everything: handing in work must not fail because an
    email did."""
    send = ast.get_source_segment(SOURCE, next(
        n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "_send"))
    assert "except Exception" in send and "logger.error" in send
