"""Learning Circles — reciprocal co-learner pairings with shared goals and journal.

Decolonial framing (Doc, 2026-06-13): no mentor over mentee. Two people form a
*learning circle* as co-learners — wisdom flows both ways. Either co-learner can
set goals and write in the shared journal; neither is the authority over the
other. The pairing is still faculty-blessed (the village forms the circle; people
don't self-select each other) and the journal is visible to both co-learners AND
to faculty — stated transparency under the minor-safety rules, not covert
surveillance. Forming a circle opens the DM channel between the two co-learners
under messages.py's minor-safety rules.

Data note: the two seats are co_learner_a_id / co_learner_b_id. The a/b order is
arbitrary (just who was selected first) and carries no hierarchy.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import users_col, learning_circles_col, circle_goals_col, circle_notes_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit

router = APIRouter(prefix="/api/learning-circles", tags=["learning-circles"])

_BRIEF = {"_id": 0, "id": 1, "name": 1, "picture": 1, "role": 1, "intent": 1}


def _brief(uid: str) -> dict:
    return users_col.find_one({"id": uid}, _BRIEF) or {"id": uid, "name": "Unknown"}


def are_co_learners(a: str, b: str) -> bool:
    """True if a and b share a learning circle (either seat order)."""
    return learning_circles_col.find_one({
        "$or": [
            {"co_learner_a_id": a, "co_learner_b_id": b},
            {"co_learner_a_id": b, "co_learner_b_id": a},
        ],
    }) is not None


def _members(circle: dict) -> tuple:
    return circle["co_learner_a_id"], circle["co_learner_b_id"]


def _get_circle_for(circle_id: str, user: dict) -> dict:
    circle = learning_circles_col.find_one({"id": circle_id}, {"_id": 0})
    if not circle:
        raise HTTPException(status_code=404, detail="Learning circle not found")
    if user["id"] not in _members(circle) and not has_permission(user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Not part of this learning circle")
    return circle


@router.get("")
def my_circles(current_user: dict = Depends(get_current_user)):
    """My learning circles. Faculty also get the full village list."""
    mine = []
    for c in learning_circles_col.find(
        {"$or": [{"co_learner_a_id": current_user["id"]}, {"co_learner_b_id": current_user["id"]}]},
        {"_id": 0},
    ).sort("created_at", -1):
        mine.append({
            **c,
            "co_learner_a": _brief(c["co_learner_a_id"]),
            "co_learner_b": _brief(c["co_learner_b_id"]),
        })

    result = {"mine": mine}
    if has_permission(current_user["role"], UserRole.FACULTY):
        all_circles = []
        for c in learning_circles_col.find({}, {"_id": 0}).sort("created_at", -1).limit(200):
            all_circles.append({**c,
                                "co_learner_a": _brief(c["co_learner_a_id"]),
                                "co_learner_b": _brief(c["co_learner_b_id"])})
        result["all"] = all_circles
    return result


@router.post("/form")
async def form_circle(request: Request, current_user: dict = Depends(get_current_user)):
    """Faculty+ form a learning circle between two co-learners."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty can form learning circles")
    data = await request.json()
    a_id, b_id = data.get("co_learner_a_id"), data.get("co_learner_b_id")
    if not a_id or not b_id or a_id == b_id:
        raise HTTPException(status_code=400, detail="Pick two different co-learners")
    for uid in (a_id, b_id):
        if not users_col.find_one({"id": uid}):
            raise HTTPException(status_code=404, detail="Co-learner not found")
    if are_co_learners(a_id, b_id):
        raise HTTPException(status_code=400, detail="They already share a circle")

    circle = {
        "id": str(uuid.uuid4()),
        "co_learner_a_id": a_id,
        "co_learner_b_id": b_id,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    learning_circles_col.insert_one(circle)
    circle.pop("_id", None)
    emit("circle.formed", current_user, "circle", circle["id"],
         meta={"co_learner_a_id": a_id, "co_learner_b_id": b_id})
    return {**circle, "co_learner_a": _brief(a_id), "co_learner_b": _brief(b_id)}


@router.delete("/{circle_id}")
def end_circle(circle_id: str, current_user: dict = Depends(get_current_user)):
    """Faculty or either co-learner can close a circle. Goals/journal are kept."""
    circle = _get_circle_for(circle_id, current_user)
    learning_circles_col.delete_one({"id": circle_id})
    a_id, b_id = _members(circle)
    emit("circle.ended", current_user, "circle", circle_id,
         meta={"co_learner_a_id": a_id, "co_learner_b_id": b_id})
    return {"success": True}


@router.get("/{circle_id}")
def circle_detail(circle_id: str, current_user: dict = Depends(get_current_user)):
    circle = _get_circle_for(circle_id, current_user)
    goals = list(circle_goals_col.find({"circle_id": circle_id}, {"_id": 0}).sort("created_at", 1))
    notes = list(circle_notes_col.find({"circle_id": circle_id}, {"_id": 0}).sort("created_at", -1).limit(50))
    return {
        **circle,
        "co_learner_a": _brief(circle["co_learner_a_id"]),
        "co_learner_b": _brief(circle["co_learner_b_id"]),
        "goals": goals,
        "notes": notes,
    }


@router.post("/{circle_id}/goals")
async def add_goal(circle_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    circle = _get_circle_for(circle_id, current_user)
    if current_user["id"] not in _members(circle):
        raise HTTPException(status_code=403, detail="Only the circle can set their goals")
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Goal text required")
    goal = {
        "id": str(uuid.uuid4()),
        "circle_id": circle_id,
        "text": text[:300],
        "done": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    circle_goals_col.insert_one(goal)
    goal.pop("_id", None)
    emit("circle.goal_added", current_user, "circle", circle_id)
    return goal


@router.put("/{circle_id}/goals/{goal_id}/toggle")
def toggle_goal(circle_id: str, goal_id: str, current_user: dict = Depends(get_current_user)):
    circle = _get_circle_for(circle_id, current_user)
    if current_user["id"] not in _members(circle):
        raise HTTPException(status_code=403, detail="Only the circle can update their goals")
    goal = circle_goals_col.find_one({"id": goal_id, "circle_id": circle_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    new_done = not goal.get("done")
    circle_goals_col.update_one({"id": goal_id}, {"$set": {"done": new_done}})
    if new_done:
        emit("circle.goal_completed", current_user, "circle", circle_id)
    return {"success": True, "done": new_done}


@router.post("/{circle_id}/notes")
async def add_note(circle_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Shared journal entry. Visible to both co-learners and to faculty."""
    circle = _get_circle_for(circle_id, current_user)
    if current_user["id"] not in _members(circle):
        raise HTTPException(status_code=403, detail="Only the circle writes in their journal")
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note text required")
    note = {
        "id": str(uuid.uuid4()),
        "circle_id": circle_id,
        "author_id": current_user["id"],
        "author_name": current_user.get("name", ""),
        "text": text[:2000],
        "created_at": datetime.now(timezone.utc),
    }
    circle_notes_col.insert_one(note)
    note.pop("_id", None)
    emit("circle.note_added", current_user, "circle", circle_id)
    return note
