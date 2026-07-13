"""Personal portfolio + individual goals (eval §6.3 — the last unbuilt
mid-term item).

The portfolio is a young person's growing body of work, reflections, and
recognitions — *theirs to keep and carry forward*. Personal goals are
learner-owned growth tracking, the individual counterpart to the collective
village/circle goals.

Ownership & visibility contract:
- Everything here belongs to its owner. Items are PRIVATE by default.
- An owner may mark an item "shared": then faculty+ and the owner's linked
  guardians can see it (the ClassDojo family loop, done with consent —
  the young person chooses what the village and family see).
- Goals are always private to their owner in v1. Nobody else can list them.
- Events emitted here carry no titles or content — the stream is
  faculty-readable (same rule as check-ins).

Recognitions (completed courses) are derived read-only from enrollments —
certificates are already generated on the fly from the same source.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import (
    portfolio_items_col, personal_goals_col, enrollments_col, courses_col,
    family_links_col, files_col,
)
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

ITEM_KINDS = {"work", "reflection"}
VISIBILITIES = {"private", "shared"}
GOAL_STATUSES = {"active", "completed", "paused"}


def _now():
    return datetime.now(timezone.utc)


def _clean_str(value, max_len):
    return (value or "").strip()[:max_len]


def _recognitions(user_id: str) -> list:
    """Completed courses, newest first — derived, not stored."""
    completed = list(
        enrollments_col.find(
            {"user_id": user_id, "status": "completed"},
            {"_id": 0, "course_id": 1, "completed_at": 1},
        )
    )
    out = []
    for e in completed:
        course = courses_col.find_one({"id": e["course_id"]}, {"_id": 0, "title": 1})
        if course:
            out.append({
                "kind": "recognition",
                "title": course["title"],
                "completed_at": e.get("completed_at"),
                "course_id": e["course_id"],
            })
    out.sort(key=lambda r: (r["completed_at"] is None, r["completed_at"]), reverse=True)
    return out


def _attach_file_meta(items: list) -> list:
    for item in items:
        if item.get("file_id"):
            f = files_col.find_one(
                {"id": item["file_id"]},
                {"_id": 0, "original_filename": 1, "file_size": 1, "mime_type": 1, "file_category": 1},
            )
            if f:
                item["file"] = {**f, "download_url": f"/api/files/{item['file_id']}/download"}
    return items


# ---------- Portfolio items ----------

@router.get("")
def my_portfolio(current_user: dict = Depends(get_current_user)):
    items = list(
        portfolio_items_col.find({"user_id": current_user["id"]}, {"_id": 0})
        .sort("created_at", -1)
    )
    return {
        "items": _attach_file_meta(items),
        "recognitions": _recognitions(current_user["id"]),
    }


@router.get("/user/{user_id}")
def view_portfolio(user_id: str, current_user: dict = Depends(get_current_user)):
    """Shared items only — for faculty+ and the owner's linked guardians."""
    if current_user["id"] == user_id:
        return my_portfolio(current_user)
    is_faculty = has_permission(current_user["role"], UserRole.FACULTY)
    is_guardian = family_links_col.find_one(
        {"guardian_id": current_user["id"], "youth_id": user_id}) is not None
    if not (is_faculty or is_guardian):
        raise HTTPException(status_code=403, detail="Access denied")
    items = list(
        portfolio_items_col.find(
            {"user_id": user_id, "visibility": "shared"}, {"_id": 0})
        .sort("created_at", -1)
    )
    return {
        "items": _attach_file_meta(items),
        "recognitions": _recognitions(user_id),
    }


@router.post("")
async def add_item(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    kind = data.get("kind")
    if kind not in ITEM_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {sorted(ITEM_KINDS)}")
    title = _clean_str(data.get("title"), 200)
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    visibility = data.get("visibility", "private")
    if visibility not in VISIBILITIES:
        raise HTTPException(status_code=400, detail="visibility must be private or shared")

    file_id = data.get("file_id")
    if file_id:
        f = files_col.find_one({"id": file_id})
        if not f or f.get("uploaded_by") != current_user["id"]:
            raise HTTPException(status_code=400, detail="file_id must be a file you uploaded")

    item = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "kind": kind,
        "title": title,
        "body": _clean_str(data.get("body"), 5000),
        "link_url": _clean_str(data.get("link_url"), 500),
        "file_id": file_id,
        "visibility": visibility,
        "created_at": _now(),
        "updated_at": _now(),
    }
    portfolio_items_col.insert_one(item)
    item.pop("_id", None)
    # No title/content in meta — the event stream is faculty-readable.
    emit("portfolio.item_added", current_user, "portfolio_item", item["id"], {"kind": kind})
    return item


@router.put("/{item_id}")
async def update_item(item_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    item = portfolio_items_col.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="This portfolio belongs to someone else")
    data = await request.json()
    update = {}
    if "title" in data:
        title = _clean_str(data.get("title"), 200)
        if not title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        update["title"] = title
    if "body" in data:
        update["body"] = _clean_str(data.get("body"), 5000)
    if "link_url" in data:
        update["link_url"] = _clean_str(data.get("link_url"), 500)
    if "visibility" in data:
        if data["visibility"] not in VISIBILITIES:
            raise HTTPException(status_code=400, detail="visibility must be private or shared")
        update["visibility"] = data["visibility"]
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    update["updated_at"] = _now()
    portfolio_items_col.update_one({"id": item_id}, {"$set": update})
    return {**{k: v for k, v in item.items() if k != "_id"}, **update}


@router.delete("/{item_id}")
def delete_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = portfolio_items_col.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="This portfolio belongs to someone else")
    portfolio_items_col.delete_one({"id": item_id})
    emit("portfolio.item_removed", current_user, "portfolio_item", item_id)
    return {"success": True}


# ---------- Personal goals ----------

@router.get("/goals")
def my_goals(current_user: dict = Depends(get_current_user)):
    goals = list(
        personal_goals_col.find({"user_id": current_user["id"]}, {"_id": 0})
        .sort("created_at", -1)
    )
    return {"goals": goals}


@router.post("/goals")
async def add_goal(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    title = _clean_str(data.get("title"), 200)
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    goal = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "title": title,
        "why": _clean_str(data.get("why"), 1000),
        "target_date": _clean_str(data.get("target_date"), 10),  # YYYY-MM-DD or ""
        "milestones": [],
        "status": "active",
        "reflection": "",
        "created_at": _now(),
        "completed_at": None,
    }
    personal_goals_col.insert_one(goal)
    goal.pop("_id", None)
    emit("goal.set", current_user, "personal_goal", goal["id"])
    return goal


def _own_goal(goal_id: str, current_user: dict) -> dict:
    goal = personal_goals_col.find_one({"id": goal_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="This goal belongs to someone else")
    return goal


@router.put("/goals/{goal_id}")
async def update_goal(goal_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    goal = _own_goal(goal_id, current_user)
    data = await request.json()
    update = {}
    if "title" in data:
        title = _clean_str(data.get("title"), 200)
        if not title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        update["title"] = title
    if "why" in data:
        update["why"] = _clean_str(data.get("why"), 1000)
    if "target_date" in data:
        update["target_date"] = _clean_str(data.get("target_date"), 10)
    if "status" in data:
        status = data["status"]
        if status not in GOAL_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {sorted(GOAL_STATUSES)}")
        update["status"] = status
        if status == "completed" and goal.get("status") != "completed":
            update["completed_at"] = _now()
            update["reflection"] = _clean_str(data.get("reflection"), 2000)
            emit("goal.completed", current_user, "personal_goal", goal_id)
        elif status != "completed":
            update["completed_at"] = None
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    personal_goals_col.update_one({"id": goal_id}, {"$set": update})
    return {**{k: v for k, v in goal.items() if k != "_id"}, **update}


@router.post("/goals/{goal_id}/milestones")
async def add_milestone(goal_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    _own_goal(goal_id, current_user)
    data = await request.json()
    text = _clean_str(data.get("text"), 300)
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    milestone = {"id": str(uuid.uuid4()), "text": text, "done": False}
    personal_goals_col.update_one({"id": goal_id}, {"$push": {"milestones": milestone}})
    return milestone


@router.put("/goals/{goal_id}/milestones/{milestone_id}/toggle")
def toggle_milestone(goal_id: str, milestone_id: str, current_user: dict = Depends(get_current_user)):
    goal = _own_goal(goal_id, current_user)
    for m in goal.get("milestones", []):
        if m["id"] == milestone_id:
            personal_goals_col.update_one(
                {"id": goal_id, "milestones.id": milestone_id},
                {"$set": {"milestones.$.done": not m["done"]}},
            )
            return {"id": milestone_id, "done": not m["done"]}
    raise HTTPException(status_code=404, detail="Milestone not found")


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: str, current_user: dict = Depends(get_current_user)):
    _own_goal(goal_id, current_user)
    personal_goals_col.delete_one({"id": goal_id})
    return {"success": True}
