from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
import hashlib
from database import live_sessions_col, courses_col, attendance_col, enrollments_col, users_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from tier_gating import require_tier
from events import emit
# Acyclic: villages.py only imports from database/middleware/models, never routes.
from routes.villages import is_village_member, _get_village, _can_steward

router = APIRouter(prefix="/api/live-sessions", tags=["live-sessions"])

ATTENDANCE_STATUSES = {"present", "late", "absent"}


def _can_take_attendance(session: dict, user: dict) -> bool:
    return session["host_id"] == user["id"] or has_permission(user["role"], UserRole.FACULTY)


def generate_room_name(session_id: str) -> str:
    """Generate a unique, URL-safe Jitsi room name."""
    hashed = hashlib.sha256(session_id.encode()).hexdigest()[:12]
    return f"ile-ubuntu-{hashed}"


@router.post("")
async def create_live_session(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create live sessions")

    data = await request.json()
    session_id = str(uuid.uuid4())

    # Village scoping (deep migration Phase 1): nullable; steward-gated when set.
    village_id = data.get("village_id")
    if village_id:
        village = _get_village(village_id)
        if not _can_steward(village, current_user):
            raise HTTPException(status_code=403, detail="Only the village's stewards schedule sessions inside it")

    session = {
        "id": session_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "course_id": data.get("course_id"),
        "village_id": village_id,
        "course_title": None,
        "host_id": current_user["id"],
        "host_name": current_user["name"],
        "host_picture": current_user.get("picture", ""),
        "room_name": generate_room_name(session_id),
        "scheduled_at": data.get("scheduled_at"),
        "status": "scheduled",
        "participants": [],
        "max_participants": data.get("max_participants", 50),
        "recording_enabled": data.get("recording_enabled", False),
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "ended_at": None,
    }

    # Fetch course title if linked
    if data.get("course_id"):
        course = courses_col.find_one({"id": data["course_id"]}, {"_id": 0, "title": 1})
        if course:
            session["course_title"] = course["title"]

    live_sessions_col.insert_one(session)
    session.pop("_id", None)
    return session


@router.get("")
def list_live_sessions(status: str = None, village_id: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    if village_id:
        query["village_id"] = village_id
    sessions = list(live_sessions_col.find(query, {"_id": 0}).sort("created_at", -1))
    return sessions


@router.get("/{session_id}")
def get_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/start")
def start_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only the host can start this session")

    live_sessions_col.update_one(
        {"id": session_id},
        {"$set": {"status": "live", "started_at": datetime.now(timezone.utc)}},
    )
    emit("live_session.started", current_user, "live_session", session_id)
    return {"success": True, "room_name": session["room_name"]}


@router.put("/{session_id}/end")
def end_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only the host can end this session")

    live_sessions_col.update_one(
        {"id": session_id},
        {"$set": {"status": "ended", "ended_at": datetime.now(timezone.utc)}},
    )
    emit("live_session.ended", current_user, "live_session", session_id,
         meta={"participants": len(session.get("participants", []))})
    return {"success": True}


@router.post("/{session_id}/join")
def join_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Village-scoped sessions: members of the village join; others don't.
    # (Hosts and faculty+ bypass, mirroring course village privacy.)
    if session.get("village_id") and session["host_id"] != current_user["id"] \
            and not has_permission(current_user["role"], UserRole.FACULTY):
        if not is_village_member(session["village_id"], current_user["id"]):
            raise HTTPException(status_code=403, detail="This session belongs to a village — join the village first")

    # Tier gating: Elder Circle required to join live sessions (hosts bypass)
    if session["host_id"] != current_user["id"]:
        require_tier(current_user, "elder_circle", "live_session")

    if session["status"] != "live" and session["host_id"] != current_user["id"]:
        raise HTTPException(status_code=400, detail="Session is not live yet")

    if current_user["id"] not in session.get("participants", []):
        live_sessions_col.update_one(
            {"id": session_id},
            {"$addToSet": {"participants": current_user["id"]}},
        )
        emit("live_session.joined", current_user, "live_session", session_id)

    return {
        "room_name": session["room_name"],
        "title": session["title"],
        "host_name": session["host_name"],
    }


@router.delete("/{session_id}")
def delete_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    live_sessions_col.delete_one({"id": session_id})
    return {"success": True}


# --- Attendance v0 (eval §10 Quick Win 4) ---

@router.get("/{session_id}/attendance")
def get_attendance(session_id: str, current_user: dict = Depends(get_current_user)):
    """Roster + attendance for a session. Host or faculty+ only.

    Roster = saved attendance records, merged with everyone who joined the
    call and (if the session is linked to a course) everyone enrolled.
    Unsaved joiners default to 'present'; unsaved enrollees to 'absent'.
    """
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _can_take_attendance(session, current_user):
        raise HTTPException(status_code=403, detail="Only the host or faculty can view attendance")

    saved = {r["user_id"]: r for r in attendance_col.find({"session_id": session_id}, {"_id": 0})}
    joined = set(session.get("participants", []))

    roster_ids = set(saved) | joined
    if session.get("course_id"):
        for e in enrollments_col.find({"course_id": session["course_id"]}, {"_id": 0, "user_id": 1}):
            roster_ids.add(e["user_id"])
    roster_ids.discard(session["host_id"])

    roster = []
    for uid in roster_ids:
        u = users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "picture": 1}) or {}
        record = saved.get(uid)
        roster.append({
            "user_id": uid,
            "name": u.get("name", "Unknown"),
            "picture": u.get("picture", ""),
            "joined_call": uid in joined,
            "status": record["status"] if record else ("present" if uid in joined else "absent"),
            "saved": record is not None,
        })
    roster.sort(key=lambda r: r["name"].lower())

    return {"session_id": session_id, "roster": roster, "taken": bool(saved)}


@router.post("/{session_id}/attendance")
async def take_attendance(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Save attendance records. Host or faculty+ only. Upserts per user."""
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _can_take_attendance(session, current_user):
        raise HTTPException(status_code=403, detail="Only the host or faculty can take attendance")

    data = await request.json()
    records = data.get("records", [])
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="records list required")

    now = datetime.now(timezone.utc)
    counts = {"present": 0, "late": 0, "absent": 0}
    for rec in records:
        uid = rec.get("user_id")
        status = rec.get("status")
        if not uid or status not in ATTENDANCE_STATUSES:
            raise HTTPException(status_code=400, detail=f"Each record needs user_id and status in {sorted(ATTENDANCE_STATUSES)}")
        u = users_col.find_one({"id": uid}, {"_id": 0, "name": 1}) or {}
        attendance_col.update_one(
            {"session_id": session_id, "user_id": uid},
            {"$set": {
                "status": status,
                "user_name": u.get("name", "Unknown"),
                "session_title": session.get("title", ""),
                "marked_by": current_user["id"],
                "marked_at": now,
            },
             "$setOnInsert": {"id": str(uuid.uuid4())}},
            upsert=True,
        )
        counts[status] += 1

    emit("attendance.recorded", current_user, "live_session", session_id, meta=counts)
    return {"success": True, "counts": counts}
