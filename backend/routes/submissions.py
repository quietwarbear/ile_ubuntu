"""Student work handed in against a lesson — files and/or links.

Deliberately separate from lesson attachments. A lesson's files are course
material everyone may read; a submission is one student's work, readable only
by that student and the course's teachers.

Two consequences that shape this module:

- Submission files are uploaded WITHOUT lesson_id or course_id. `list_files`
  filters on those and applies no enrolment check, so stamping either would
  expose every student's work to every signed-in user.
- `/api/files/{id}/download` is unauthenticated by design, because lesson
  material is embedded in tags that cannot send a session header. Submission
  files are therefore fetched through `download-link` here, which authenticates
  first and then hands back a short-lived URL.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
from pathlib import Path
import uuid

import storage
from database import (
    submissions_col,
    files_col,
    lessons_col,
    courses_col,
    enrollments_col,
)
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit
# Acyclic: courses.py never imports from here.
from routes.courses import _is_course_staff, _lesson_is_open
import teacher_alerts

router = APIRouter(
    prefix="/api/courses/{course_id}/lessons/{lesson_id}/submissions",
    tags=["submissions"],
)

NOTE_MAX = 5000
MAX_LINKS = 10
MAX_FILES = 10


def _verify_access(course_id: str, lesson_id: str, current_user: dict):
    """Returns (course, lesson, is_staff). Students must be enrolled and the
    lesson must actually be open to them."""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    lesson = lessons_col.find_one({"id": lesson_id, "course_id": course_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if _is_course_staff(course, current_user) or has_permission(
        current_user["role"], UserRole.FACULTY
    ):
        return course, lesson, True

    if not enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id}
    ):
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    if not _lesson_is_open(lesson):
        raise HTTPException(status_code=404, detail="Lesson not found")
    return course, lesson, False


def _clean_links(raw) -> list:
    """Accept http(s) links only — a Google Doc, Drive file, or anything else
    the teacher can open. Anything else is a paste error or worse."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="links must be a list")
    links = []
    for item in raw:
        url = (item or "").strip() if isinstance(item, str) else ""
        if not url:
            continue
        if not url.lower().startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400, detail=f"Links must start with http:// or https:// — got '{url[:60]}'"
            )
        links.append(url)
    if len(links) > MAX_LINKS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_LINKS} links per submission")
    return links


def _claim_files(raw, current_user: dict, submission_id: str) -> list:
    """Take ownership of freshly uploaded files. Only the uploader's own files
    qualify, and only ones not already bound to a lesson or another
    submission — otherwise a student could attach course material, or someone
    else's work, to their own hand-in."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="file_ids must be a list")
    ids = [str(i).strip() for i in raw if str(i or "").strip()]
    if len(ids) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"At most {MAX_FILES} files per submission")

    claimed = []
    for file_id in ids:
        record = files_col.find_one({"id": file_id})
        if not record:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        if record.get("uploaded_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only attach your own uploads")
        bound = record.get("submission_id")
        if bound and bound != submission_id:
            raise HTTPException(status_code=400, detail="That file belongs to another submission")
        if record.get("lesson_id"):
            raise HTTPException(status_code=400, detail="That file is lesson material, not your work")
        files_col.update_one({"id": file_id}, {"$set": {"submission_id": submission_id}})
        claimed.append(file_id)
    return claimed


def _file_summaries(file_ids: list) -> list:
    """Names and sizes only. The bytes come from download-link, which checks
    who is asking."""
    if not file_ids:
        return []
    records = files_col.find(
        {"id": {"$in": file_ids}},
        {"_id": 0, "id": 1, "original_filename": 1, "file_size": 1, "mime_type": 1},
    )
    return list(records)


def _present(submission: dict) -> dict:
    out = dict(submission)
    out.pop("_id", None)
    out["files"] = _file_summaries(out.get("file_ids") or [])
    return out


def _drop_files(file_ids: list):
    """Remove stored objects and records for a withdrawn submission."""
    for record in files_col.find({"id": {"$in": list(file_ids or [])}}):
        if record.get("s3_key"):
            storage.delete_object(record["s3_key"])
        elif record.get("file_path"):
            path = Path(record["file_path"])
            if path.exists():
                path.unlink()
    files_col.delete_many({"id": {"$in": list(file_ids or [])}})


@router.get("")
def list_submissions(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Teachers see the whole class. A student sees only their own work."""
    _, _, is_staff = _verify_access(course_id, lesson_id, current_user)
    query = {"course_id": course_id, "lesson_id": lesson_id}
    if not is_staff:
        query["student_id"] = current_user["id"]
    found = list(submissions_col.find(query).sort("submitted_at", -1))
    return {"submissions": [_present(s) for s in found], "total": len(found)}


@router.get("/mine")
def my_submission(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    _verify_access(course_id, lesson_id, current_user)
    found = submissions_col.find_one(
        {"course_id": course_id, "lesson_id": lesson_id, "student_id": current_user["id"]}
    )
    return {"submission": _present(found) if found else None}


@router.post("")
async def submit_work(course_id: str, lesson_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Hand in work, or replace what was handed in before. One submission per
    student per lesson — resubmitting updates it rather than piling up copies,
    so the teacher always reads the current version."""
    course, lesson, _ = _verify_access(course_id, lesson_id, current_user)
    data = await request.json()

    note = (data.get("note") or "").strip()
    if len(note) > NOTE_MAX:
        raise HTTPException(status_code=400, detail=f"Note is too long (limit {NOTE_MAX} characters)")
    links = _clean_links(data.get("links"))

    existing = submissions_col.find_one(
        {"course_id": course_id, "lesson_id": lesson_id, "student_id": current_user["id"]}
    )
    submission_id = existing["id"] if existing else str(uuid.uuid4())
    file_ids = _claim_files(data.get("file_ids"), current_user, submission_id)

    if not note and not links and not file_ids:
        raise HTTPException(
            status_code=400, detail="Attach a file, add a link, or write a note before submitting"
        )

    now = datetime.now(timezone.utc)
    if existing:
        # Files dropped from the resubmission are deleted, not orphaned in the
        # bucket paying rent forever.
        removed = [f for f in (existing.get("file_ids") or []) if f not in file_ids]
        _drop_files(removed)
        submissions_col.update_one(
            {"id": submission_id},
            {"$set": {"note": note, "links": links, "file_ids": file_ids, "updated_at": now}},
        )
    else:
        submissions_col.insert_one({
            "id": submission_id,
            "course_id": course_id,
            "lesson_id": lesson_id,
            "student_id": current_user["id"],
            "student_name": current_user.get("name", "Student"),
            "student_email": current_user.get("email", ""),
            "note": note,
            "links": links,
            "file_ids": file_ids,
            "submitted_at": now,
            "updated_at": now,
        })
        emit(
            "lesson.work_submitted", current_user, "lesson", lesson_id,
            meta={"course_id": course_id, "submission_id": submission_id},
        )

    teacher_alerts.notify_submission(
        course, lesson, current_user.get("name", "A student"),
        is_update=bool(existing), exclude_id=current_user["id"],
    )
    return {"submission": _present(submissions_col.find_one({"id": submission_id}))}


@router.get("/{submission_id}/download-link/{file_id}")
def submission_download_link(course_id: str, lesson_id: str, submission_id: str, file_id: str, current_user: dict = Depends(get_current_user)):
    """A short-lived URL for one submitted file. This exists because
    /api/files/{id}/download authenticates nobody — student work must not be
    readable by anyone holding the id."""
    _, _, is_staff = _verify_access(course_id, lesson_id, current_user)
    submission = submissions_col.find_one(
        {"id": submission_id, "course_id": course_id, "lesson_id": lesson_id}
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission["student_id"] != current_user["id"] and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    if file_id not in (submission.get("file_ids") or []):
        raise HTTPException(status_code=404, detail="File is not part of this submission")

    record = files_col.find_one({"id": file_id})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    name = record.get("original_filename") or "submission"
    mime = record.get("mime_type") or "application/octet-stream"
    if record.get("s3_key"):
        return {"url": storage.presigned_get(record["s3_key"], name, mime, inline=False), "filename": name}
    # Local dev fallback only; production runs on S3.
    return {"url": f"/api/files/{file_id}/download", "filename": name}


@router.delete("/{submission_id}")
def withdraw_submission(course_id: str, lesson_id: str, submission_id: str, current_user: dict = Depends(get_current_user)):
    """The student who handed it in, or a teacher. Takes the uploaded files
    with it — a withdrawn submission should leave nothing behind."""
    _, _, is_staff = _verify_access(course_id, lesson_id, current_user)
    submission = submissions_col.find_one(
        {"id": submission_id, "course_id": course_id, "lesson_id": lesson_id}
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission["student_id"] != current_user["id"] and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")

    _drop_files(submission.get("file_ids") or [])
    submissions_col.delete_one({"id": submission_id})
    return {"success": True}
