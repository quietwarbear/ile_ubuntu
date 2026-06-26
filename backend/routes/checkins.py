"""SEL check-ins — a light daily pulse (eval §6.3): mood, connection, confidence.

Privacy contract (affirming, not policing — eval §7 guardrails):
- The optional note is PRIVATE to its author. It is never returned to
  faculty, guardians, or anyone else, and never leaves this collection.
- The three 1–5 scores feed the Community Dashboard's Wellness dimension
  (per member and collective). The check-in UI states this plainly.
- The wellness.checked_in event carries NO scores in its meta — the event
  stream is faculty-readable and must not leak how someone said they feel.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from database import checkins_col
from middleware import get_current_user
from events import emit

router = APIRouter(prefix="/api/checkins", tags=["checkins"])

FIELDS = ("mood", "connected", "confident")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@router.post("")
async def check_in(request: Request, current_user: dict = Depends(get_current_user)):
    """Record today's check-in (re-checking-in replaces today's answers)."""
    data = await request.json()
    scores = {}
    for f in FIELDS:
        v = data.get(f)
        if not isinstance(v, int) or not 1 <= v <= 5:
            raise HTTPException(status_code=400, detail=f"{f} must be 1–5")
        scores[f] = v
    note = (data.get("note") or "").strip()[:500]

    day = _today()
    existing = checkins_col.find_one({"user_id": current_user["id"], "day": day})
    checkins_col.update_one(
        {"user_id": current_user["id"], "day": day},
        {"$set": {**scores, "note": note, "updated_at": datetime.now(timezone.utc)},
         "$setOnInsert": {
             "id": str(uuid.uuid4()),
             "user_id": current_user["id"],
             "day": day,
             "created_at": datetime.now(timezone.utc),
         }},
        upsert=True,
    )
    if not existing:
        # No scores in meta — see privacy contract above.
        emit("wellness.checked_in", current_user, "user", current_user["id"])
    return {"success": True, "day": day}


@router.get("/me")
def my_checkins(current_user: dict = Depends(get_current_user)):
    """My own history (notes included — they're mine)."""
    history = list(
        checkins_col.find({"user_id": current_user["id"]}, {"_id": 0})
        .sort("day", -1).limit(30)
    )
    return {
        "checked_in_today": any(c["day"] == _today() for c in history),
        "history": history,
    }
