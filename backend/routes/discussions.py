"""Class discussion — student-named topics, each holding one thread.

Course-wide, unlike lesson_comments which hang off a single lesson. Anyone in
the class may open a topic and anyone may reply, teachers included.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid

from database import (
    course_topics_col,
    course_topic_posts_col,
    courses_col,
    enrollments_col,
)
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit
# Acyclic: courses.py imports database/middleware/models/villages, never this.
from routes.courses import _is_course_staff

router = APIRouter(
    prefix="/api/courses/{course_id}/discussion",
    tags=["course-discussion"],
)

TITLE_MAX = 140
POST_MAX = 20000


def _verify_access(course_id: str, current_user: dict):
    """Everyone in the class reads and posts: enrolled students, the course's
    own staff, and faculty+. Returns (course, is_staff)."""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if _is_course_staff(course, current_user) or has_permission(
        current_user["role"], UserRole.FACULTY
    ):
        return course, True
    enrolled = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id}
    )
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    return course, False


def _author_fields(current_user: dict, is_staff: bool) -> dict:
    return {
        "author_id": current_user["id"],
        "author_name": current_user.get("name", "Anonymous"),
        "author_role": current_user.get("role", "student"),
        "is_instructor": is_staff,
    }


def _require_text(value, label: str, limit: int) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{label} is required")
    if len(text) > limit:
        raise HTTPException(
            status_code=400, detail=f"{label} is too long (limit {limit} characters)"
        )
    return text


def _get_topic(course_id: str, topic_id: str) -> dict:
    topic = course_topics_col.find_one({"id": topic_id, "course_id": course_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


# --- Topics ---

@router.get("/topics")
def list_topics(course_id: str, current_user: dict = Depends(get_current_user)):
    """Pinned first, then whichever has been talked in most recently."""
    _verify_access(course_id, current_user)
    topics = list(
        course_topics_col.find({"course_id": course_id}, {"_id": 0}).sort(
            [("pinned", -1), ("last_activity_at", -1)]
        )
    )
    return {"topics": topics, "total": len(topics)}


@router.post("/topics")
async def create_topic(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Open a topic. The opening message is stored as the thread's first post
    so a topic and its replies read uniformly."""
    _, is_staff = _verify_access(course_id, current_user)
    data = await request.json()
    title = _require_text(data.get("title"), "Topic title", TITLE_MAX)
    content = _require_text(data.get("content"), "Opening message", POST_MAX)

    now = datetime.now(timezone.utc)
    author = _author_fields(current_user, is_staff)
    topic = {
        "id": str(uuid.uuid4()),
        "course_id": course_id,
        "title": title,
        **author,
        "pinned": False,
        "locked": False,
        "reply_count": 0,
        "created_at": now,
        "updated_at": now,
        "last_activity_at": now,
    }
    course_topics_col.insert_one(topic)
    topic.pop("_id", None)

    opening = {
        "id": str(uuid.uuid4()),
        "topic_id": topic["id"],
        "course_id": course_id,
        **author,
        "content": content,
        "is_opening_post": True,
        "edited": False,
        "created_at": now,
        "updated_at": now,
    }
    course_topic_posts_col.insert_one(opening)
    opening.pop("_id", None)

    emit(
        "course.topic_opened", current_user, "course", course_id,
        meta={"topic_id": topic["id"], "title": title},
    )
    return {"topic": topic, "post": opening}


@router.get("/topics/{topic_id}")
def get_topic(course_id: str, topic_id: str, current_user: dict = Depends(get_current_user)):
    _verify_access(course_id, current_user)
    topic = course_topics_col.find_one({"id": topic_id, "course_id": course_id}, {"_id": 0})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    posts = list(
        course_topic_posts_col.find({"topic_id": topic_id}, {"_id": 0}).sort("created_at", 1)
    )
    return {"topic": topic, "posts": posts}


@router.delete("/topics/{topic_id}")
def delete_topic(course_id: str, topic_id: str, current_user: dict = Depends(get_current_user)):
    """The person who opened it, or a teacher. Takes the whole thread with it."""
    _, is_staff = _verify_access(course_id, current_user)
    topic = _get_topic(course_id, topic_id)
    if topic["author_id"] != current_user["id"] and not is_staff:
        raise HTTPException(
            status_code=403, detail="Only the author or a teacher can delete this topic"
        )
    course_topic_posts_col.delete_many({"topic_id": topic_id})
    course_topics_col.delete_one({"id": topic_id})
    emit("course.topic_deleted", current_user, "course", course_id, meta={"topic_id": topic_id})
    return {"success": True}


@router.post("/topics/{topic_id}/pin")
async def set_topic_pinned(course_id: str, topic_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Teachers only — keeps a topic at the top of the list."""
    _, is_staff = _verify_access(course_id, current_user)
    if not is_staff:
        raise HTTPException(status_code=403, detail="Only a teacher can pin a topic")
    _get_topic(course_id, topic_id)
    pinned = bool((await request.json()).get("pinned", True))
    course_topics_col.update_one({"id": topic_id}, {"$set": {"pinned": pinned}})
    return {"success": True, "pinned": pinned}


@router.post("/topics/{topic_id}/lock")
async def set_topic_locked(course_id: str, topic_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Teachers only — closes a thread to further student replies."""
    _, is_staff = _verify_access(course_id, current_user)
    if not is_staff:
        raise HTTPException(status_code=403, detail="Only a teacher can lock a topic")
    _get_topic(course_id, topic_id)
    locked = bool((await request.json()).get("locked", True))
    course_topics_col.update_one({"id": topic_id}, {"$set": {"locked": locked}})
    return {"success": True, "locked": locked}


# --- Posts ---

@router.post("/topics/{topic_id}/posts")
async def create_post(course_id: str, topic_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Reply in a thread. A locked topic still accepts a teacher's post, so a
    thread can be closed with a final word rather than silence."""
    _, is_staff = _verify_access(course_id, current_user)
    topic = _get_topic(course_id, topic_id)
    if topic.get("locked") and not is_staff:
        raise HTTPException(status_code=403, detail="This topic is closed to new replies")

    content = _require_text((await request.json()).get("content"), "Message", POST_MAX)
    now = datetime.now(timezone.utc)
    post = {
        "id": str(uuid.uuid4()),
        "topic_id": topic_id,
        "course_id": course_id,
        **_author_fields(current_user, is_staff),
        "content": content,
        "is_opening_post": False,
        "edited": False,
        "created_at": now,
        "updated_at": now,
    }
    course_topic_posts_col.insert_one(post)
    post.pop("_id", None)

    course_topics_col.update_one(
        {"id": topic_id},
        {"$inc": {"reply_count": 1}, "$set": {"last_activity_at": now, "updated_at": now}},
    )
    emit(
        "course.topic_replied", current_user, "course", course_id,
        meta={"topic_id": topic_id, "post_id": post["id"]},
    )
    return post


@router.put("/posts/{post_id}")
async def update_post(course_id: str, post_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Authors edit their own words. A teacher may remove a post but never
    rewrite it under someone else's name."""
    _verify_access(course_id, current_user)
    post = course_topic_posts_col.find_one({"id": post_id, "course_id": course_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")

    content = _require_text((await request.json()).get("content"), "Message", POST_MAX)
    course_topic_posts_col.update_one(
        {"id": post_id},
        {"$set": {"content": content, "edited": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return course_topic_posts_col.find_one({"id": post_id}, {"_id": 0})


@router.delete("/posts/{post_id}")
def delete_post(course_id: str, post_id: str, current_user: dict = Depends(get_current_user)):
    """The author or a teacher. The opening post cannot go on its own — that
    would leave a thread with no beginning; delete the topic instead."""
    _, is_staff = _verify_access(course_id, current_user)
    post = course_topic_posts_col.find_one({"id": post_id, "course_id": course_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"] and not is_staff:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    if post.get("is_opening_post"):
        raise HTTPException(
            status_code=400,
            detail="This message opens the topic — delete the topic instead",
        )

    course_topic_posts_col.delete_one({"id": post_id})
    course_topics_col.update_one(
        {"id": post["topic_id"], "reply_count": {"$gt": 0}},
        {"$inc": {"reply_count": -1}},
    )
    return {"success": True}
