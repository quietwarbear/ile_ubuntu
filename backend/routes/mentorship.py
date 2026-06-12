"""Mentorship module — mentor <-> mentee pairing with shared goals and journal.

Safety model (eval §6.3/§7 guardrails): pairings are created by faculty+ —
the village blesses the relationship; mentors cannot self-select mentees.
The pair's journal is visible to both participants AND to faculty (stated
transparency, not covert surveillance). Pairing opens the DM channel between
mentor and mentee under the minor-safety rules in messages.py.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import users_col, mentorship_pairs_col, mentorship_goals_col, mentorship_notes_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit

router = APIRouter(prefix="/api/mentorship", tags=["mentorship"])

_BRIEF = {"_id": 0, "id": 1, "name": 1, "picture": 1, "role": 1, "intent": 1}


def _brief(uid: str) -> dict:
    return users_col.find_one({"id": uid}, _BRIEF) or {"id": uid, "name": "Unknown"}


def are_mentor_pair(a: str, b: str) -> bool:
    return mentorship_pairs_col.find_one({
        "$or": [{"mentor_id": a, "mentee_id": b}, {"mentor_id": b, "mentee_id": a}],
    }) is not None


def _get_pairing_for(pairing_id: str, user: dict) -> dict:
    pairing = mentorship_pairs_col.find_one({"id": pairing_id}, {"_id": 0})
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing not found")
    is_participant = user["id"] in (pairing["mentor_id"], pairing["mentee_id"])
    if not is_participant and not has_permission(user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Not part of this mentorship")
    return pairing


@router.get("")
def my_pairings(current_user: dict = Depends(get_current_user)):
    """My pairings (as mentor or mentee). Faculty also get the full village list."""
    mine = []
    for p in mentorship_pairs_col.find(
        {"$or": [{"mentor_id": current_user["id"]}, {"mentee_id": current_user["id"]}]},
        {"_id": 0},
    ).sort("created_at", -1):
        mine.append({
            **p,
            "mentor": _brief(p["mentor_id"]),
            "mentee": _brief(p["mentee_id"]),
            "my_side": "mentor" if p["mentor_id"] == current_user["id"] else "mentee",
        })

    result = {"mine": mine}
    if has_permission(current_user["role"], UserRole.FACULTY):
        all_pairs = []
        for p in mentorship_pairs_col.find({}, {"_id": 0}).sort("created_at", -1).limit(200):
            all_pairs.append({**p, "mentor": _brief(p["mentor_id"]), "mentee": _brief(p["mentee_id"])})
        result["all"] = all_pairs
    return result


@router.post("/pair")
async def create_pairing(request: Request, current_user: dict = Depends(get_current_user)):
    """Faculty+ pair a mentor with a mentee."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty can create mentorship pairings")
    data = await request.json()
    mentor_id, mentee_id = data.get("mentor_id"), data.get("mentee_id")
    if not mentor_id or not mentee_id or mentor_id == mentee_id:
        raise HTTPException(status_code=400, detail="Pick a mentor and a different mentee")
    for uid, label in ((mentor_id, "Mentor"), (mentee_id, "Mentee")):
        if not users_col.find_one({"id": uid}):
            raise HTTPException(status_code=404, detail=f"{label} not found")
    if are_mentor_pair(mentor_id, mentee_id):
        raise HTTPException(status_code=400, detail="They're already paired")

    pairing = {
        "id": str(uuid.uuid4()),
        "mentor_id": mentor_id,
        "mentee_id": mentee_id,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    mentorship_pairs_col.insert_one(pairing)
    pairing.pop("_id", None)
    emit("mentorship.paired", current_user, "mentorship", pairing["id"],
         meta={"mentor_id": mentor_id, "mentee_id": mentee_id})
    return {**pairing, "mentor": _brief(mentor_id), "mentee": _brief(mentee_id)}


@router.delete("/pair/{pairing_id}")
def end_pairing(pairing_id: str, current_user: dict = Depends(get_current_user)):
    """Faculty or either participant can end a pairing. Goals/journal are kept."""
    pairing = _get_pairing_for(pairing_id, current_user)
    mentorship_pairs_col.delete_one({"id": pairing_id})
    emit("mentorship.unpaired", current_user, "mentorship", pairing_id,
         meta={"mentor_id": pairing["mentor_id"], "mentee_id": pairing["mentee_id"]})
    return {"success": True}


@router.get("/{pairing_id}")
def pairing_detail(pairing_id: str, current_user: dict = Depends(get_current_user)):
    pairing = _get_pairing_for(pairing_id, current_user)
    goals = list(mentorship_goals_col.find({"pairing_id": pairing_id}, {"_id": 0}).sort("created_at", 1))
    notes = list(mentorship_notes_col.find({"pairing_id": pairing_id}, {"_id": 0}).sort("created_at", -1).limit(50))
    return {
        **pairing,
        "mentor": _brief(pairing["mentor_id"]),
        "mentee": _brief(pairing["mentee_id"]),
        "goals": goals,
        "notes": notes,
    }


@router.post("/{pairing_id}/goals")
async def add_goal(pairing_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    pairing = _get_pairing_for(pairing_id, current_user)
    if current_user["id"] not in (pairing["mentor_id"], pairing["mentee_id"]):
        raise HTTPException(status_code=403, detail="Only the pair can set their goals")
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Goal text required")
    goal = {
        "id": str(uuid.uuid4()),
        "pairing_id": pairing_id,
        "text": text[:300],
        "done": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    mentorship_goals_col.insert_one(goal)
    goal.pop("_id", None)
    emit("mentorship.goal_added", current_user, "mentorship", pairing_id)
    return goal


@router.put("/{pairing_id}/goals/{goal_id}/toggle")
def toggle_goal(pairing_id: str, goal_id: str, current_user: dict = Depends(get_current_user)):
    pairing = _get_pairing_for(pairing_id, current_user)
    if current_user["id"] not in (pairing["mentor_id"], pairing["mentee_id"]):
        raise HTTPException(status_code=403, detail="Only the pair can update their goals")
    goal = mentorship_goals_col.find_one({"id": goal_id, "pairing_id": pairing_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    new_done = not goal.get("done")
    mentorship_goals_col.update_one({"id": goal_id}, {"$set": {"done": new_done}})
    if new_done:
        emit("mentorship.goal_completed", current_user, "mentorship", pairing_id)
    return {"success": True, "done": new_done}


@router.post("/{pairing_id}/notes")
async def add_note(pairing_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Shared journal entry. Visible to the pair and to faculty."""
    pairing = _get_pairing_for(pairing_id, current_user)
    if current_user["id"] not in (pairing["mentor_id"], pairing["mentee_id"]):
        raise HTTPException(status_code=403, detail="Only the pair writes in their journal")
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note text required")
    note = {
        "id": str(uuid.uuid4()),
        "pairing_id": pairing_id,
        "author_id": current_user["id"],
        "author_name": current_user.get("name", ""),
        "text": text[:2000],
        "created_at": datetime.now(timezone.utc),
    }
    mentorship_notes_col.insert_one(note)
    note.pop("_id", None)
    emit("mentorship.note_added", current_user, "mentorship", pairing_id)
    return note
