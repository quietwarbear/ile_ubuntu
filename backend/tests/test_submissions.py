"""Student submission rules.

Student work is the most sensitive thing in the course, and the two paths that
could expose it — the unauthenticated /api/files download and the unchecked
course-wide file listing — already existed before submissions did. These tests
pin the containment.

Validation helpers run for real; access rules are asserted against the
committed handlers, since the module needs FastAPI and a live Mongo.
"""

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
SRC = BACKEND / "routes" / "submissions.py"
SOURCE = SRC.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class _Boom(Exception):
    def __init__(self, status_code=None, detail=None):
        self.status_code = status_code
        self.detail = detail


def _node(name):
    for n in TREE.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return n
    raise AssertionError(f"{name}() not found in submissions.py")


def _body(name):
    return ast.get_source_segment(SOURCE, _node(name))


CONSTANTS = ("NOTE_MAX", "MAX_LINKS", "MAX_FILES")


def _constant_nodes():
    return [
        n for n in TREE.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in CONSTANTS for t in n.targets)
    ]


def _load(name, extra=None):
    # Carry the module's own caps in rather than restating them here.
    body = _constant_nodes() + [_node(name)]
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    ns = {"HTTPException": _Boom}
    ns.update(extra or {})
    exec(compile(module, str(SRC), "exec"), ns)
    return ns


_LINKS_NS = _load("_clean_links")
clean_links = _LINKS_NS["_clean_links"]
MAX_LINKS = _LINKS_NS["MAX_LINKS"]


# --- links ------------------------------------------------------------------

def test_google_and_https_links_pass():
    urls = ["https://docs.google.com/document/d/abc/edit", "http://example.org/paper"]
    assert clean_links(urls) == urls


def test_blank_entries_are_dropped():
    assert clean_links(["  ", "", None, "https://ok.test"]) == ["https://ok.test"]


@pytest.mark.parametrize(
    "bad",
    ["javascript:alert(1)", "file:///etc/passwd", "docs.google.com/x", "data:text/html,x"],
)
def test_non_http_schemes_are_refused(bad):
    """A teacher clicks these. javascript: and file: must never make it in."""
    with pytest.raises(_Boom) as raised:
        clean_links([bad])
    assert raised.value.status_code == 400


def test_link_count_is_capped():
    with pytest.raises(_Boom):
        clean_links([f"https://x.test/{i}" for i in range(MAX_LINKS + 1)])


def test_links_must_be_a_list():
    with pytest.raises(_Boom):
        clean_links("https://x.test")


def test_no_links_is_fine():
    assert clean_links(None) == []


# --- containment ------------------------------------------------------------

def test_submission_files_are_never_stamped_with_course_or_lesson_id():
    """list_files filters on those two fields and applies no enrolment check,
    and /api/files/{id}/download authenticates nobody. Stamping either would
    publish every student's work to every signed-in user."""
    src = _body("_claim_files")
    assert 'files_col.update_one({"id": file_id}, {"$set": {"submission_id": submission_id}})' in src
    # It may *read* lesson_id to reject course material; it must never write it.
    assert '"$set": {"lesson_id"' not in src
    assert '"$set": {"course_id"' not in src
    assert '"course_id": course_id' not in src


def test_file_listings_exclude_submitted_work():
    files_src = (BACKEND / "routes" / "files.py").read_text(encoding="utf-8")
    assert files_src.count('query["submission_id"] = {"$exists": False}') == 2


def test_a_student_cannot_attach_someone_elses_upload():
    assert 'record.get("uploaded_by") != current_user["id"]' in _body("_claim_files")


def test_a_student_cannot_attach_lesson_material_as_their_own_work():
    assert 'record.get("lesson_id")' in _body("_claim_files")


def test_a_file_cannot_be_stolen_from_another_submission():
    src = _body("_claim_files")
    assert "bound and bound != submission_id" in src


# --- who reads what ---------------------------------------------------------

def test_students_see_only_their_own_submission_in_the_listing():
    src = _body("list_submissions")
    assert 'if not is_staff:' in src
    assert 'query["student_id"] = current_user["id"]' in src


def test_download_link_checks_the_caller():
    src = _body("submission_download_link")
    assert 'submission["student_id"] != current_user["id"] and not is_staff' in src


def test_download_link_refuses_a_file_from_another_submission():
    assert 'file_id not in (submission.get("file_ids") or [])' in _body("submission_download_link")


def test_withdrawing_is_owner_or_teacher_and_removes_the_files():
    src = _body("withdraw_submission")
    assert 'submission["student_id"] != current_user["id"] and not is_staff' in src
    assert "_drop_files" in src


def test_resubmitting_deletes_the_files_it_drops():
    """Otherwise abandoned uploads sit in the bucket forever."""
    src = _body("submit_work")
    assert "removed = [f for f in (existing.get(\"file_ids\") or []) if f not in file_ids]" in src
    assert "_drop_files(removed)" in src


def test_an_unreleased_lesson_accepts_no_submissions():
    src = _body("_verify_access")
    assert "_lesson_is_open(lesson)" in src
    assert "enrollments_col.find_one" in src


def test_an_empty_submission_is_refused():
    assert "if not note and not links and not file_ids:" in _body("submit_work")
