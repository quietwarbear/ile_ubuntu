from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import json
import uuid
from database import users_col
from middleware import get_current_user

router = APIRouter(prefix="/api/push", tags=["push"])


@router.post("/subscribe")
async def subscribe_push(request: Request, current_user: dict = Depends(get_current_user)):
    """Store a push subscription for the current user."""
    data = await request.json()
    subscription = data.get("subscription")
    if not subscription:
        raise HTTPException(status_code=400, detail="Subscription data required")

    # Store subscription on user document
    users_col.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "push_subscription": subscription,
            "push_subscribed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"success": True}


@router.delete("/subscribe")
async def unsubscribe_push(current_user: dict = Depends(get_current_user)):
    """Remove push subscription."""
    users_col.update_one(
        {"id": current_user["id"]},
        {"$unset": {"push_subscription": "", "push_subscribed_at": ""}},
    )
    return {"success": True}


@router.get("/status")
async def push_status(current_user: dict = Depends(get_current_user)):
    """Check if user has push subscription."""
    user = users_col.find_one({"id": current_user["id"]}, {"_id": 0, "push_subscription": 1})
    return {"subscribed": bool(user and user.get("push_subscription"))}


@router.get("/vapid-key")
async def get_vapid_key():
    """Return the public VAPID key for push subscription."""
    # Generate static VAPID keys (in production, store these in env)
    import os
    vapid_public = os.environ.get("VAPID_PUBLIC_KEY", "")
    if not vapid_public:
        # Generate keys if not set
        from pywebpush import webpush
        try:
            from py_vapid import Vapid
            vapid = Vapid()
            vapid.generate_keys()
            vapid_public = vapid.public_key_urlsafe()
            os.environ["VAPID_PUBLIC_KEY"] = vapid_public
            os.environ["VAPID_PRIVATE_KEY"] = vapid.private_key_urlsafe()
        except Exception:
            return {"public_key": ""}

    return {"public_key": vapid_public}


async def send_push_to_user(user_id: str, title: str, body: str, url: str = "/dashboard"):
    """Send push notification to a specific user (fire-and-forget)."""
    import os
    import asyncio

    user = users_col.find_one({"id": user_id}, {"_id": 0, "push_subscription": 1})
    if not user or not user.get("push_subscription"):
        return

    subscription = user["push_subscription"]
    vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not vapid_private:
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/logo192.png",
        "badge": "/logo192.png",
    })

    try:
        from pywebpush import webpush, WebPushException
        await asyncio.to_thread(
            webpush,
            subscription_info=subscription,
            data=payload,
            vapid_private_key=vapid_private,
            vapid_claims={"sub": "mailto:noreply@ileubuntu.com"},
        )
    except Exception as e:
        # Subscription may have expired
        if "410" in str(e) or "404" in str(e):
            users_col.update_one(
                {"id": user_id},
                {"$unset": {"push_subscription": "", "push_subscribed_at": ""}},
            )
