from fastapi import Header, HTTPException
from typing import Optional
from datetime import datetime, timezone
from database import sessions_col, users_col


async def get_current_user(x_session_id: Optional[str] = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required")

    session = sessions_col.find_one({"session_id": x_session_id})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Handle both timezone-aware and naive datetimes from MongoDB
    expires_at = session["expires_at"]
    now = datetime.now(timezone.utc)
    
    # If expires_at is naive, make it aware (assume UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < now:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = users_col.find_one({"id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
