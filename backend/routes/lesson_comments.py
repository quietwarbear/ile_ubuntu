"""Lesson comments — threaded discussion on course lessons."""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import lesson_comments_col, lessons_col, courses_col, enrollments_col, notifications_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(
    prefix="/api/courses/{course_id}/lessons/{lesson_id}/comments",
    tags=["lesson-comments"],
)


def _verify_access(course_id: str, lesson_id: str, current_user: dict):
    """Verify the lesson exists and user has access (enrolled or instructor)."""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lesson = lessons_col.find_one({"id": lesson_id, "course_id": course_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Instructors and faculty+ always have access
    if course["instructor_id"] == current_user["id"] or has_permission(current_user["role"], UserRole.FACULTY):
        return course, lesson

    # Students must be enrolled
    enrollment = enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id})
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    return course, lesson


@router.get("")
async def list_comments(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Get all comments for a lesson, including replies (threaded)."""
    _verify_access(course_id, lesson_id, current_user)

    comments = list(lesson_comments_col.find(
        {"lesson_id": lesson_id, "parent_id": None},
        {"_id": 0},
    ).sort("created_at", 1))

    # Attach replies to each top-level comment
    for comment in comments:
        replies = list(lesson_comments_col.find(
            {"parent_id": comment["id"]},
            {"_id": 0},
        ).sort("created_at", 1))
        comment["replies"] = replies

    total = lesson_comments_col.count_documents({"lesson_id": lesson_id})
    return {"comments": comments, "total": total}


@router.post("")
async def create_comment(
    course_id: str, lesson_id: str,
    request: Request, current_user: dict = Depends(get_current_user),
):
    """Post a comment on a lesson."""
    course, lesson = _verify_access(course_id, lesson_id, current_user)

    data = await request.json()
    content = (data.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment content is required")

    parent_id = data.get("parent_id")
    if parent_id:
        parent = lesson_comments_col.find_one({"id": parent_id, "lesson_id": lesson_id})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    is_instructor = (
        course["instructor_id"] == current_user["id"]
        or has_permission(current_user["role"], UserRole.FACULTY)
    )

    comment = {
        "id": str(uuid.uuid4()),
        "lesson_id": lesson_id,
        "course_id": course_id,
        "parent_id": parent_id,
        "author_id": current_user["id"],
        "author_name": current_user.get("name", "Anonymous"),
        "author_role": current_user.get("role", "student"),
        "is_instructor": is_instructor,
        "content": content,
        "edited": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    lesson_comments_col.insert_one(comment)
    comment.pop("_id", None)

    # Notify the course instructor when a student comments
    if not is_instructor:
        try:
            notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": course["instructor_id"],
                "type": "lesson_comment",
                "title": f"New comment on {lesson['title']}",
                "body": f"{current_user.get('name', 'A student')} commented on your lesson",
                "data": {"course_id": course_id, "lesson_id": lesson_id, "comment_id": comment["id"]},
                "read": False,
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass

    # Notify the parent comment author when someone replies
    if parent_id:
        parent = lesson_comments_col.find_one({"id": parent_id})
        if parent and parent["author_id"] != current_user["id"]:
            try:
                notifications_col.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": parent["author_id"],
                    "type": "comment_reply",
                    "title": f"Reply to your comment",
                    "body": f"{current_user.get('name', 'Someone')} replied to your comment on {lesson['title']}",
                    "data": {"course_id": course_id, "lesson_id": lesson_id, "comment_id": comment["id"]},
                    "read": False,
                    "created_at": datetime.now(timezone.utc),
                })
            except Exception:
                pass

    return comment


@router.put("/{comment_id}")
async def update_comment(
    course_id: str, lesson_id: str, comment_id: str,
    request: Request, current_user: dict = Depends(get_current_user),
):
    """Edit a comment (author only)."""
    comment = lesson_comments_col.find_one({"id": comment_id, "lesson_id": lesson_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Can only edit your own comments")

    data = await request.json()
    content = (data.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment content is required")

    lesson_comments_col.update_one(
        {"id": comment_id},
        {"$set": {"content": content, "edited": True, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = lesson_comments_col.find_one({"id": comment_id}, {"_id": 0})
    return updated


@router.delete("/{comment_id}")
async def delete_comment(
    course_id: str, lesson_id: str, comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a comment (author or instructor/admin)."""
    comment = lesson_comments_col.find_one({"id": comment_id, "lesson_id": lesson_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    course = courses_col.find_one({"id": course_id})
    is_author = comment["author_id"] == current_user["id"]
    is_admin = course and (
        course["instructor_id"] == current_user["id"]
        or has_permission(current_user["role"], UserRole.ADMIN)
    )

    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete the comment and all its replies
    lesson_comments_col.delete_many({"parent_id": comment_id})
    lesson_comments_col.delete_one({"id": comment_id})

    return {"success": True}
