"""Class discussion rules.

The validation helpers run for real; the moderation model is asserted against
the committed handlers. The module itself needs FastAPI and a live Mongo, so
nothing here imports it.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "routes" / "discussions.py"
SOURCE = SRC.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _handler(name):
    for node in TREE.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name}() not found in discussions.py")


def _body(name):
    return ast.get_source_segment(SOURCE, _handler(name))


def _load(name):
    node = _handler(name)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    ns = {"HTTPException": _Boom}
    exec(compile(module, str(SRC), "exec"), ns)
    return ns[name]


class _Boom(Exception):
    def __init__(self, status_code=None, detail=None):
        self.status_code = status_code
        self.detail = detail


require_text = _load("_require_text")


# --- input validation --------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   ", None, "\n\t"])
def test_blank_text_is_rejected(value):
    with pytest.raises(_Boom) as raised:
        require_text(value, "Message", 100)
    assert raised.value.status_code == 400


def test_text_is_trimmed():
    assert require_text("  hello  ", "Message", 100) == "hello"


def test_overlong_text_is_rejected():
    with pytest.raises(_Boom) as raised:
        require_text("x" * 101, "Message", 100)
    assert raised.value.status_code == 400


def test_text_at_the_limit_is_accepted():
    assert require_text("x" * 100, "Message", 100) == "x" * 100


# --- moderation model --------------------------------------------------------

def test_a_teacher_cannot_rewrite_someone_elses_post():
    """Deleting is moderation; editing another person's words under their name
    is not. update_post must check authorship alone, with no staff bypass."""
    src = _body("update_post")
    assert 'post["author_id"] != current_user["id"]' in src
    assert "is_staff" not in src, "staff must not be able to edit another author's post"


def test_a_teacher_can_delete_someone_elses_post():
    src = _body("delete_post")
    assert 'post["author_id"] != current_user["id"] and not is_staff' in src


def test_the_opening_post_cannot_be_deleted_alone():
    """Removing it would leave a thread with no beginning."""
    src = _body("delete_post")
    assert 'post.get("is_opening_post")' in src


def test_locked_topic_blocks_students_but_not_teachers():
    src = _body("create_post")
    assert 'topic.get("locked") and not is_staff' in src


@pytest.mark.parametrize("handler", ["set_topic_pinned", "set_topic_locked"])
def test_pin_and_lock_are_teacher_only(handler):
    assert "if not is_staff:" in _body(handler)


def test_topic_deletion_allows_author_or_teacher():
    src = _body("delete_topic")
    assert 'topic["author_id"] != current_user["id"] and not is_staff' in src
    assert "course_topic_posts_col.delete_many" in src, "thread must go with the topic"


def test_replying_bumps_the_topic():
    """The list is ordered by last activity; without this bump a busy thread
    sinks and the ordering silently lies."""
    src = _body("create_post")
    assert '"$inc": {"reply_count": 1}' in src
    assert "last_activity_at" in src


def test_listing_is_ordered_pinned_then_recent():
    assert '[("pinned", -1), ("last_activity_at", -1)]' in _body("list_topics")


def test_enrolment_is_required_to_read_or_post():
    src = _body("_verify_access")
    assert "enrollments_col.find_one" in src
    assert "Not enrolled in this course" in src
