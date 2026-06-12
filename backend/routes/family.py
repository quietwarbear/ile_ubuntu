"""Family ecosystem v1 — guardian <-> youth linkage (minor-safety foundation).

How linking works: a learner (typically a young person) has a family code on
their account. A guardian enters that code on the Family page and becomes
linked. Either side can remove the link. Guardians see a warm growth summary
of their young person — progress and activity, not raw grades.

This is the technical foundation, not legal compliance: review COPPA/FERPA
posture with counsel before marketing to under-13s.
"""

import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from database import users_col, family_links_col, enrollments_col, courses_col, events_col
from middleware import get_current_user
from events import emit

router = APIRouter(prefix="/api/family", tags=["family"])

_PUBLIC_USER = {"_id": 0, "id": 1, "name": 1, "picture": 1, "is_minor": 1}


def _user_brief(uid: str) -> dict:
    u = users_col.find_one({"id": uid}, _PUBLIC_USER) or {"id": uid, "name": "Unknown"}
    return u


def is_guardian_of(guardian_id: str, youth_id: str) -> bool:
    return family_links_col.find_one({"guardian_id": guardian_id, "youth_id": youth_id}) is not None


@router.get("")
def my_family(current_user: dict = Depends(get_current_user)):
    """Both sides of my family graph + my family code."""
    guardians = [
        {**_user_brief(l["guardian_id"]), "linked_at": l.get("created_at")}
        for l in family_links_col.find({"youth_id": current_user["id"]}, {"_id": 0})
    ]
    youth = [
        {**_user_brief(l["youth_id"]), "linked_at": l.get("created_at")}
        for l in family_links_col.find({"guardian_id": current_user["id"]}, {"_id": 0})
    ]
    return {
        "family_code": current_user.get("family_code"),
        "guardians": guardians,
        "youth": youth,
    }


@router.post("/code")
def generate_family_code(current_user: dict = Depends(get_current_user)):
    """Create (or rotate) my family code. Rotating invalidates the old code
    for NEW links; existing links remain."""
    code = secrets.token_urlsafe(5)[:6].replace("_", "x").replace("-", "y").upper()
    users_col.update_one({"id": current_user["id"]}, {"$set": {"family_code": code}})
    return {"family_code": code}


@router.post("/link")
async def link_youth(request: Request, current_user: dict = Depends(get_current_user)):
    """Redeem a family code: the current user becomes a guardian of its owner."""
    data = await request.json()
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Family code required")

    youth = users_col.find_one({"family_code": code})
    if not youth:
        raise HTTPException(status_code=404, detail="That code doesn't match anyone. Double-check it with your young person.")
    if youth["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="That's your own code")
    if is_guardian_of(current_user["id"], youth["id"]):
        return {"success": True, "message": "Already linked", "youth": _user_brief(youth["id"])}

    family_links_col.insert_one({
        "id": str(uuid.uuid4()),
        "guardian_id": current_user["id"],
        "youth_id": youth["id"],
        "code_used": code,
        "created_at": datetime.now(timezone.utc),
    })
    emit("family.linked", current_user, "user", youth["id"])
    return {"success": True, "youth": _user_brief(youth["id"])}


@router.delete("/link/{other_id}")
def unlink(other_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a family link from either side."""
    result = family_links_col.delete_one({
        "$or": [
            {"guardian_id": current_user["id"], "youth_id": other_id},
            {"guardian_id": other_id, "youth_id": current_user["id"]},
        ]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No such family link")
    emit("family.unlinked", current_user, "user", other_id)
    return {"success": True}


@router.get("/youth/{youth_id}/summary")
def youth_summary(youth_id: str, current_user: dict = Depends(get_current_user)):
    """Guardian-only growth summary: how the young person is showing up —
    progress and participation, told warmly. Not a gradebook."""
    if not is_guardian_of(current_user["id"], youth_id):
        raise HTTPException(status_code=403, detail="You're not linked to this young person")

    youth = _user_brief(youth_id)

    enrollments = []
    for e in enrollments_col.find({"user_id": youth_id}, {"_id": 0, "course_id": 1, "progress": 1, "status": 1}):
        course = courses_col.find_one({"id": e["course_id"]}, {"_id": 0, "title": 1})
        enrollments.append({
            "course_title": (course or {}).get("title", "A course"),
            "progress": round(e.get("progress", 0)),
            "completed": e.get("status") == "completed",
        })

    since = datetime.now(timezone.utc) - timedelta(days=7)
    week_counts = {}
    pipeline = [
        {"$match": {"user_id": youth_id, "created_at": {"$gte": since}}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
    ]
    for row in events_col.aggregate(pipeline):
        week_counts[row["_id"]] = row["count"]

    return {
        "youth": youth,
        "enrollments": enrollments,
        "this_week": {
            "lessons_completed": week_counts.get("lesson.completed", 0),
            "live_sessions_joined": week_counts.get("live_session.joined", 0),
            "posts_and_replies": week_counts.get("post.created", 0) + week_counts.get("post.replied", 0),
            "quizzes_attempted": week_counts.get("quiz.attempted", 0),
            "courses_completed": week_counts.get("course.completed", 0),
        },
    }
