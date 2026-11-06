"""Quiz questions must stay behind the lesson's student release boundary."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path


QUIZZES = Path(__file__).resolve().parents[1] / "routes" / "quizzes.py"
SOURCE = QUIZZES.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _load_release_check():
    node = next(
        node for node in TREE.body
        if isinstance(node, ast.FunctionDef) and node.name == "_lesson_is_released"
    )
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {"datetime": datetime, "timezone": timezone}
    exec(compile(module, str(QUIZZES), "exec"), namespace)
    return namespace["_lesson_is_released"]


is_released = _load_release_check()


def test_open_lesson_quiz_is_available():
    assert is_released({"hidden": False, "available_at": None}) is True


def test_hidden_lesson_quiz_is_withheld():
    assert is_released({"hidden": True}) is False


def test_scheduled_quiz_is_withheld_until_release_time():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    assert is_released({"available_at": future}) is False
    assert is_released({"available_at": past}) is True


def test_invalid_release_time_fails_closed():
    assert is_released({"available_at": "not-a-time"}) is False


class QuizHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


def _load_quiz_reader(lesson):
    from copy import deepcopy
    from types import SimpleNamespace

    node = deepcopy(next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "get_quiz"))
    node.decorator_list = []
    node.args.defaults = [ast.Constant(False), ast.Constant(None)]
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {
        "_get_lesson": lambda course_id, lesson_id: lesson,
        "quizzes_col": SimpleNamespace(find_one=lambda *args: {"questions": [{"id": "q1", "correct_answer": "private", "explanation": "private"}]}),
        "has_permission": lambda *args: False,
        "UserRole": SimpleNamespace(FACULTY="faculty"),
        "_lesson_is_released": is_released,
        "HTTPException": QuizHTTPException,
    }
    exec(compile(module, str(QUIZZES), "exec"), namespace)
    return namespace["get_quiz"]


def test_student_reads_released_quiz_without_answer_key():
    quiz = _load_quiz_reader({"hidden": False})("course", "lesson", False, {"role": "student"})
    assert quiz["questions"] == [{"id": "q1"}]


def test_student_cannot_read_hidden_quiz():
    import pytest
    with pytest.raises(QuizHTTPException) as exc:
        _load_quiz_reader({"hidden": True})("course", "lesson", False, {"role": "student"})
    assert exc.value.status_code == 404
