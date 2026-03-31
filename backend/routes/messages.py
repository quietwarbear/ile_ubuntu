from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import messages_col, notifications_col
from middleware import get_current_user
from typing import Optional

router = APIRouter(prefix="/api", tags=["messaging"])


@router.post("/messages")
async def send_message(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    msg = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "sender_name": current_user["name"],
        "recipient_id": data["recipient_id"],
        "class_id": data.get("class_id"),
        "message": data["message"],
        "created_at": datetime.now(timezone.utc),
    }
    messages_col.insert_one(msg)

    notification = {
        "id": str(uuid.uuid4()),
        "user_id": data["recipient_id"],
        "title": "New Message",
        "message": f"You have a new message from {current_user['name']}",
        "type": "message",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    notifications_col.insert_one(notification)

    msg.pop("_id", None)
    return msg


@router.get("/messages")
async def get_messages(recipient_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if recipient_id:
        query = {
            "$or": [
                {"sender_id": current_user["id"], "recipient_id": recipient_id},
                {"sender_id": recipient_id, "recipient_id": current_user["id"]},
            ]
        }
    else:
        query = {
            "$or": [
                {"sender_id": current_user["id"]},
                {"recipient_id": current_user["id"]},
            ]
        }

    msgs = list(messages_col.find(query, {"_id": 0}).sort("created_at", -1))
    return msgs


@router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifs = list(
        notifications_col.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1)
    )
    return notifs


@router.put("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    notifications_col.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}},
    )
    return {"success": True}
