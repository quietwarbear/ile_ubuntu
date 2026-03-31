from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
import hashlib
from database import live_sessions_col, courses_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/live-sessions", tags=["live-sessions"])


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

    session = {
        "id": session_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "course_id": data.get("course_id"),
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
async def list_live_sessions(status: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    sessions = list(live_sessions_col.find(query, {"_id": 0}).sort("created_at", -1))
    return sessions


@router.get("/{session_id}")
async def get_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/start")
async def start_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only the host can start this session")

    live_sessions_col.update_one(
        {"id": session_id},
        {"$set": {"status": "live", "started_at": datetime.now(timezone.utc)}},
    )
    return {"success": True, "room_name": session["room_name"]}


@router.put("/{session_id}/end")
async def end_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only the host can end this session")

    live_sessions_col.update_one(
        {"id": session_id},
        {"$set": {"status": "ended", "ended_at": datetime.now(timezone.utc)}},
    )
    return {"success": True}


@router.post("/{session_id}/join")
async def join_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "live" and session["host_id"] != current_user["id"]:
        raise HTTPException(status_code=400, detail="Session is not live yet")

    if current_user["id"] not in session.get("participants", []):
        live_sessions_col.update_one(
            {"id": session_id},
            {"$addToSet": {"participants": current_user["id"]}},
        )

    return {
        "room_name": session["room_name"],
        "title": session["title"],
        "host_name": session["host_name"],
    }


@router.delete("/{session_id}")
async def delete_live_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    live_sessions_col.delete_one({"id": session_id})
    return {"success": True}
