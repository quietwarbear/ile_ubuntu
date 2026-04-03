"""
RevenueCat webhook handler for server-side subscription events.
Handles renewals, cancellations, billing issues, and refunds.

Webhook URL: https://ile-ubuntu.org/api/webhook/revenuecat
Configure in RevenueCat Dashboard → Project Settings → Integrations → Webhooks
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
import os
import hmac
import hashlib
from database import users_col, payment_transactions_col

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])

REVENUECAT_WEBHOOK_SECRET = os.environ.get("REVENUECAT_WEBHOOK_SECRET", "")

# Product ID → tier mapping
PRODUCT_ID_TO_TIER = {
    "com.ileubuntu.scholar.monthly": "scholar",
    "com.ileubuntu.scholar.annual": "scholar",
    "com.ileubuntu.elder.monthly": "elder_circle",
    "com.ileubuntu.elder.annual": "elder_circle",
    # Android product IDs (same mapping)
    "ile_ubuntu_scholar:scholar-monthly": "scholar",
    "ile_ubuntu_scholar:scholar-yearly": "scholar",
    "ile_ubuntu_elder:elder-monthly": "elder_circle",
    "ile_ubuntu_elder:elder-yearly": "elder_circle",
}


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify RevenueCat webhook signature."""
    if not REVENUECAT_WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    expected = hmac.new(
        REVENUECAT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/revenuecat")
async def revenuecat_webhook(request: Request):
    """Handle RevenueCat webhook events."""
    body = await request.body()

    # Verify signature if configured
    signature = request.headers.get("X-RevenueCat-Signature", "")
    if REVENUECAT_WEBHOOK_SECRET and not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event = data.get("event", {})
    event_type = event.get("type", "")
    app_user_id = event.get("app_user_id", "")
    product_id = event.get("product_id", "")

    if not app_user_id:
        return {"status": "ignored", "reason": "no app_user_id"}

    # Resolve tier from product ID
    tier_id = PRODUCT_ID_TO_TIER.get(product_id)

    now = datetime.now(timezone.utc).isoformat()

    if event_type in ("INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE"):
        # Activate or renew subscription
        if tier_id:
            users_col.update_one(
                {"id": app_user_id},
                {"$set": {
                    "subscription_tier": tier_id,
                    "subscription_status": "active",
                    "subscription_product_id": product_id,
                    "subscription_renewed_at": now,
                }},
            )
            payment_transactions_col.insert_one({
                "user_id": app_user_id,
                "tier_id": tier_id,
                "product_id": product_id,
                "event_type": event_type,
                "payment_status": "paid",
                "payment_method": "in_app_purchase",
                "created_at": now,
            })

    elif event_type in ("CANCELLATION", "EXPIRATION"):
        # Downgrade to free tier
        users_col.update_one(
            {"id": app_user_id},
            {"$set": {
                "subscription_tier": "explorer",
                "subscription_status": "cancelled" if event_type == "CANCELLATION" else "expired",
                "subscription_ended_at": now,
            }},
        )
        payment_transactions_col.insert_one({
            "user_id": app_user_id,
            "event_type": event_type,
            "product_id": product_id,
            "payment_status": event_type.lower(),
            "created_at": now,
        })

    elif event_type == "BILLING_ISSUE":
        # Flag billing issue but keep tier active (grace period)
        users_col.update_one(
            {"id": app_user_id},
            {"$set": {
                "subscription_status": "billing_issue",
                "subscription_billing_issue_at": now,
            }},
        )

    elif event_type == "SUBSCRIBER_ALIAS":
        # RevenueCat user alias — log but no action needed
        pass

    return {"status": "ok", "event_type": event_type}
