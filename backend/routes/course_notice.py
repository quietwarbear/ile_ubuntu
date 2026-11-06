"""Course notice (item I7).

An organizer-written note at the top of a course page: sharing rules, credits,
acknowledgments. Markdown, written in the same WysiwygEditor as lessons and
rendered by the same viewer (react-markdown, no raw HTML).

Who reads it: the course's staff (owner, co-teachers, platform admins) and
enrolled students. Everyone else gets 404, the same answer as a course with
no notice, so a non-member can't tell whether one exists.

Who writes it: the course's staff. Platform-wide roles that aren't on this
course's staff don't.

The notice lives in its own collection, not on the course document, so the
catalog, search and other course lists can never carry it.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import course_notices_col, courses_col, enrollments_col
from middleware import get_current_user
from routes.courses import _is_course_staff

router = APIRouter(prefix="/api/courses", tags=["course-notice"])

MAX_NOTICE_CHARS = 20000


def _course_or_404(course_id: str) -> dict:
    course = courses_col.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def can_read_notice(course: dict, user: dict) -> bool:
    if _is_course_staff(course, user):
        return True
    return enrollments_col.find_one({"user_id": user["id"], "course_id": course["id"]}) is not None


def _public(row: dict) -> dict:
    return {
        "course_id": row["course_id"],
        "body": row.get("body", ""),
        "updated_at": row.get("updated_at"),
    }


@router.get("/{course_id}/notice")
def get_notice(course_id: str, current_user: dict = Depends(get_current_user)):
    course = _course_or_404(course_id)
    if not can_read_notice(course, current_user):
        raise HTTPException(status_code=404, detail="No notice")
    row = course_notices_col.find_one({"course_id": course_id}, {"_id": 0})
    if not row or not (row.get("body") or "").strip():
        raise HTTPException(status_code=404, detail="No notice")
    return _public(row)


@router.put("/{course_id}/notice")
async def put_notice(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = _course_or_404(course_id)
    if not _is_course_staff(course, current_user):
        raise HTTPException(status_code=403, detail="Only this course's staff can edit its notice")
    data = await request.json()
    body = data.get("body") if isinstance(data, dict) else None
    if body is None:
        body = ""
    if not isinstance(body, str):
        raise HTTPException(status_code=400, detail="body must be text")
    if len(body) > MAX_NOTICE_CHARS:
        raise HTTPException(status_code=400, detail=f"The notice can be at most {MAX_NOTICE_CHARS} characters")
    body = body.strip()
    if not body:
        course_notices_col.delete_one({"course_id": course_id})
        return {"course_id": course_id, "body": "", "updated_at": None}
    now = datetime.now(timezone.utc)
    course_notices_col.update_one(
        {"course_id": course_id},
        {"$set": {"body": body, "updated_at": now, "updated_by": current_user["id"]},
         "$setOnInsert": {"course_id": course_id, "created_at": now}},
        upsert=True,
    )
    return {"course_id": course_id, "body": body, "updated_at": now}
