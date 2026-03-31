from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import live_sessions_col, users_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/session-records", tags=["session-records"])


@router.get("")
async def list_session_records(current_user: dict = Depends(get_current_user)):
    """List all ended sessions with their recording metadata."""
    sessions = list(live_sessions_col.find(
        {"status": "ended"},
        {"_id": 0}
    ).sort("ended_at", -1).limit(50))

    for s in sessions:
        host = users_col.find_one({"id": s.get("host_id")}, {"_id": 0, "name": 1, "picture": 1})
        s["host_name"] = host.get("name", "Unknown") if host else "Unknown"
        s["host_picture"] = host.get("picture") if host else None

    return sessions


@router.get("/{session_id}")
async def get_session_record(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific session's recording metadata."""
    session = live_sessions_col.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    host = users_col.find_one({"id": session.get("host_id")}, {"_id": 0, "name": 1, "picture": 1})
    session["host_name"] = host.get("name", "Unknown") if host else "Unknown"

    # Get attendee details
    attendees = []
    for uid in session.get("attendees", []):
        u = users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "picture": 1, "role": 1})
        if u:
            attendees.append(u)
    session["attendee_details"] = attendees

    return session


@router.put("/{session_id}/notes")
async def update_session_notes(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Add notes, key takeaways, and tags to a session record."""
    data = await request.json()
    session = live_sessions_col.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Only host or faculty+ can add notes
    if session["host_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only host or faculty can edit notes")

    update = {}
    if "notes" in data:
        update["notes"] = data["notes"]
    if "key_takeaways" in data:
        update["key_takeaways"] = data["key_takeaways"]
    if "tags" in data:
        update["tags"] = data["tags"]

    update["notes_updated_at"] = datetime.now(timezone.utc).isoformat()
    update["notes_updated_by"] = current_user["id"]

    live_sessions_col.update_one({"id": session_id}, {"$set": update})
    return {"success": True}


@router.get("/{session_id}/export")
async def export_session_record(session_id: str, current_user: dict = Depends(get_current_user)):
    """Export session record as CSV-friendly data."""
    session = live_sessions_col.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attendees = []
    for uid in session.get("attendees", []):
        u = users_col.find_one({"id": uid}, {"_id": 0, "name": 1, "email": 1, "role": 1})
        if u:
            attendees.append(u)

    return {
        "session_title": session.get("title", "Untitled"),
        "host": session.get("host_id"),
        "status": session.get("status"),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "attendee_count": len(session.get("attendees", [])),
        "attendees": attendees,
        "notes": session.get("notes", ""),
        "key_takeaways": session.get("key_takeaways", []),
        "tags": session.get("tags", []),
    }
