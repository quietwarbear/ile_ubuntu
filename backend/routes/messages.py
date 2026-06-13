from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import messages_col, notifications_col, users_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from typing import Optional

router = APIRouter(prefix="/api", tags=["messaging"])

_STAFF = UserRole.FACULTY  # faculty/elder/admin may message minors


def _dm_allowed(sender: dict, recipient: dict) -> bool:
    """Minor-safety rule: if either party is a minor, direct messages are
    limited to staff (faculty+) and linked guardians. Minor-to-minor and
    minor-to-unrelated-adult DMs are blocked in v1 (deliberately conservative;
    relax with cohort/village context later)."""
    if not (sender.get("is_minor") or recipient.get("is_minor")):
        return True
    if has_permission(sender.get("role"), _STAFF) or has_permission(recipient.get("role"), _STAFF):
        return True
    from routes.family import is_guardian_of
    if is_guardian_of(sender["id"], recipient["id"]) or is_guardian_of(recipient["id"], sender["id"]):
        return True
    # Faculty-blessed learning circles open the channel too
    from routes.learning_circles import are_co_learners
    return are_co_learners(sender["id"], recipient["id"])


@router.post("/messages")
async def send_message(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    recipient = users_col.find_one({"id": data["recipient_id"]})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if not _dm_allowed(current_user, recipient):
        raise HTTPException(
            status_code=403,
            detail="To keep young people safe, direct messages with minors are limited to educators and linked family.",
        )
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
def get_messages(recipient_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
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
def get_notifications(current_user: dict = Depends(get_current_user)):
    notifs = list(
        notifications_col.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1)
    )
    return notifs


@router.put("/notifications/{notification_id}/read")
def mark_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    notifications_col.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}},
    )
    return {"success": True}
