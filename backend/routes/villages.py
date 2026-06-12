"""Village — the community container (eval §6.1: the village, not the course,
is the primitive).

A Village is a bounded community with a season and a place: youth, educators,
mentors, elders, and families belong to it WITH a relationship role — a web,
not a ladder. village_role describes how someone belongs; it grants no
platform permissions (those stay on user.role).

v1 foundation: entity + membership + collective goals + cohort attachment.
The deeper migration (courses/sessions scoped inside villages, village feed
as home) is the next dedicated slice.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import villages_col, users_col, cohorts_col, courses_col, live_sessions_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit

router = APIRouter(prefix="/api/villages", tags=["villages"])

VILLAGE_ROLES = ("youth", "educator", "mentor", "elder", "family")

_BRIEF = {"_id": 0, "id": 1, "name": 1, "picture": 1}


def _brief(uid: str) -> dict:
    return users_col.find_one({"id": uid}, _BRIEF) or {"id": uid, "name": "Unknown"}


def _get_village(village_id: str) -> dict:
    v = villages_col.find_one({"id": village_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Village not found")
    return v


def _can_steward(village: dict, user: dict) -> bool:
    """Stewards: faculty+, or members holding educator/elder roles in this village."""
    if has_permission(user["role"], UserRole.FACULTY):
        return True
    return any(m["user_id"] == user["id"] and m["village_role"] in ("educator", "elder")
               for m in village.get("members", []))


@router.post("")
async def create_village(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can found a village")
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="A village needs a name")
    village = {
        "id": str(uuid.uuid4()),
        "name": name[:120],
        "description": (data.get("description") or "").strip()[:1000],
        "season": (data.get("season") or "").strip()[:60],
        "place": (data.get("place") or "").strip()[:120],
        "members": [{
            "user_id": current_user["id"],
            "village_role": "elder" if current_user["role"] in ("elder", "admin") else "educator",
            "joined_at": datetime.now(timezone.utc),
        }],
        "goals": [],
        "cohort_ids": [],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    villages_col.insert_one(village)
    village.pop("_id", None)
    emit("village.created", current_user, "village", village["id"], meta={"name": name})
    return village


@router.get("")
def list_villages(current_user: dict = Depends(get_current_user)):
    """My villages; faculty also see every village."""
    mine = list(villages_col.find(
        {"members.user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1))
    result = {"mine": mine}
    if has_permission(current_user["role"], UserRole.FACULTY):
        result["all"] = list(villages_col.find({}, {"_id": 0}).sort("created_at", -1).limit(100))
    return result


@router.get("/{village_id}")
def village_detail(village_id: str, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    is_member = any(m["user_id"] == current_user["id"] for m in v.get("members", []))
    if not is_member and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="This village's circle isn't yours yet")

    members = [{**m, **_brief(m["user_id"])} for m in v.get("members", [])]
    cohorts = [
        {"id": c["id"], "name": c["name"], "member_count": len(c.get("members", []))}
        for c in cohorts_col.find({"id": {"$in": v.get("cohort_ids", [])}}, {"_id": 0, "id": 1, "name": 1, "members": 1})
    ]
    return {**v, "members": members, "cohorts": cohorts, "can_steward": _can_steward(v, current_user)}


@router.post("/{village_id}/members")
async def add_member(village_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only the village's stewards can welcome members")
    data = await request.json()
    user_id, village_role = data.get("user_id"), data.get("village_role")
    if village_role not in VILLAGE_ROLES:
        raise HTTPException(status_code=400, detail=f"village_role must be one of {VILLAGE_ROLES}")
    if not users_col.find_one({"id": user_id}):
        raise HTTPException(status_code=404, detail="User not found")
    if any(m["user_id"] == user_id for m in v.get("members", [])):
        raise HTTPException(status_code=400, detail="Already part of this village")

    villages_col.update_one({"id": village_id}, {"$push": {"members": {
        "user_id": user_id,
        "village_role": village_role,
        "joined_at": datetime.now(timezone.utc),
    }}})
    emit("village.member_added", current_user, "village", village_id,
         meta={"user_id": user_id, "village_role": village_role})
    return {"success": True}


@router.delete("/{village_id}/members/{user_id}")
def remove_member(village_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if user_id != current_user["id"] and not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards can do that")
    villages_col.update_one({"id": village_id}, {"$pull": {"members": {"user_id": user_id}}})
    emit("village.member_removed", current_user, "village", village_id, meta={"user_id": user_id})
    return {"success": True}


@router.post("/{village_id}/goals")
async def add_goal(village_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards set village goals")
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Goal text required")
    goal = {"id": str(uuid.uuid4()), "text": text[:300], "done": False,
            "created_at": datetime.now(timezone.utc)}
    villages_col.update_one({"id": village_id}, {"$push": {"goals": goal}})
    emit("village.goal_added", current_user, "village", village_id)
    return goal


@router.put("/{village_id}/goals/{goal_id}/toggle")
def toggle_goal(village_id: str, goal_id: str, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards update village goals")
    goal = next((g for g in v.get("goals", []) if g["id"] == goal_id), None)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    new_done = not goal.get("done")
    villages_col.update_one(
        {"id": village_id, "goals.id": goal_id},
        {"$set": {"goals.$.done": new_done}},
    )
    if new_done:
        emit("village.goal_completed", current_user, "village", village_id)
    return {"success": True, "done": new_done}


@router.post("/{village_id}/cohorts")
async def attach_cohort(village_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards attach cohorts")
    data = await request.json()
    cohort_id = data.get("cohort_id")
    if not cohorts_col.find_one({"id": cohort_id}):
        raise HTTPException(status_code=404, detail="Cohort not found")
    villages_col.update_one({"id": village_id}, {"$addToSet": {"cohort_ids": cohort_id}})
    cohorts_col.update_one({"id": cohort_id}, {"$set": {"village_id": village_id}})
    return {"success": True}


# --- Content scoping (deep migration Phase 1): courses & live sessions live
# inside a village. Attach/detach mirrors cohort attachment: steward-gated,
# the content document carries village_id. ---

@router.post("/{village_id}/courses")
async def attach_course(village_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards bring courses into the village")
    data = await request.json()
    course_id = data.get("course_id")
    if not courses_col.find_one({"id": course_id}):
        raise HTTPException(status_code=404, detail="Course not found")
    courses_col.update_one({"id": course_id}, {"$set": {"village_id": village_id}})
    emit("village.course_attached", current_user, "village", village_id, meta={"course_id": course_id})
    return {"success": True}


@router.delete("/{village_id}/courses/{course_id}")
def detach_course(village_id: str, course_id: str, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards can do that")
    course = courses_col.find_one({"id": course_id, "village_id": village_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course is not attached to this village")
    update = {"village_id": None}
    # A course can't stay members-only with no village to be a member of.
    if course.get("visibility") == "village":
        update["visibility"] = "unlisted"
    courses_col.update_one({"id": course_id}, {"$set": update})
    return {"success": True}


@router.post("/{village_id}/live-sessions")
async def attach_live_session(village_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards bring sessions into the village")
    data = await request.json()
    session_id = data.get("session_id")
    if not live_sessions_col.find_one({"id": session_id}):
        raise HTTPException(status_code=404, detail="Session not found")
    live_sessions_col.update_one({"id": session_id}, {"$set": {"village_id": village_id}})
    emit("village.session_attached", current_user, "village", village_id, meta={"session_id": session_id})
    return {"success": True}


@router.delete("/{village_id}/live-sessions/{session_id}")
def detach_live_session(village_id: str, session_id: str, current_user: dict = Depends(get_current_user)):
    v = _get_village(village_id)
    if not _can_steward(v, current_user):
        raise HTTPException(status_code=403, detail="Only stewards can do that")
    result = live_sessions_col.update_one(
        {"id": session_id, "village_id": village_id}, {"$set": {"village_id": None}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session is not attached to this village")
    return {"success": True}


def is_village_member(village_id: str, user_id: str) -> bool:
    """Membership check for other routes (courses, live sessions)."""
    return villages_col.find_one(
        {"id": village_id, "members.user_id": user_id}, {"_id": 1}) is not None


def user_village_ids(user_id: str) -> list:
    """All village ids the user belongs to (for catalog visibility clauses)."""
    return [v["id"] for v in villages_col.find(
        {"members.user_id": user_id}, {"_id": 0, "id": 1})]
