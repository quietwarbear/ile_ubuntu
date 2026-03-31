from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import os
import uuid
from dotenv import load_dotenv
from database import payment_transactions_col, users_col
from middleware import get_current_user
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

load_dotenv()

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

# Membership tiers — amounts defined server-side only
MEMBERSHIP_TIERS = {
    "explorer": {
        "name": "Explorer",
        "price": 0.0,
        "description": "Free access to public courses and community",
        "features": ["Browse public courses", "Community access", "Basic archives"],
    },
    "scholar": {
        "name": "Scholar",
        "price": 19.99,
        "description": "Full course enrollment and cohort access",
        "features": ["All Explorer features", "Unlimited course enrollment", "Cohort membership", "Knowledge spaces", "Priority support"],
    },
    "elder_circle": {
        "name": "Elder Circle",
        "price": 49.99,
        "description": "Premium access with governance privileges",
        "features": ["All Scholar features", "Live teaching sessions", "Protected archives", "Governance participation", "Custom branding"],
    },
}


@router.get("/tiers")
async def get_tiers():
    return list(MEMBERSHIP_TIERS.values())


@router.get("/my-subscription")
async def get_my_subscription(current_user: dict = Depends(get_current_user)):
    user = users_col.find_one({"id": current_user["id"]}, {"_id": 0})
    tier = user.get("subscription_tier", "explorer")
    is_bypassed = user.get("role") in ("faculty", "elder", "admin")

    enrollment_count = 0
    if not is_bypassed:
        from database import enrollments_col
        enrollment_count = enrollments_col.count_documents({"user_id": current_user["id"]})

    limits = {
        "explorer": {"max_enrollments": 2, "cohorts": False, "spaces": False, "live_sessions": False, "restricted_archives": False},
        "scholar": {"max_enrollments": 999999, "cohorts": True, "spaces": True, "live_sessions": False, "restricted_archives": False},
        "elder_circle": {"max_enrollments": 999999, "cohorts": True, "spaces": True, "live_sessions": True, "restricted_archives": True},
    }

    return {
        "tier": tier,
        "subscription_status": user.get("subscription_status", "active"),
        "subscribed_at": user.get("subscribed_at"),
        "is_bypassed": is_bypassed,
        "enrollment_count": enrollment_count,
        "limits": limits.get(tier, limits["explorer"]),
    }


@router.post("/checkout")
async def create_checkout(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    tier_id = data.get("tier_id")
    origin_url = data.get("origin_url")

    if not tier_id or tier_id not in MEMBERSHIP_TIERS:
        raise HTTPException(status_code=400, detail="Invalid membership tier")

    tier = MEMBERSHIP_TIERS[tier_id]
    if tier["price"] == 0:
        # Free tier — just update the user
        users_col.update_one(
            {"id": current_user["id"]},
            {"$set": {
                "subscription_tier": tier_id,
                "subscription_status": "active",
                "subscribed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {"success": True, "tier": tier_id, "free": True}

    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    success_url = f"{origin_url}/subscriptions?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/subscriptions"

    metadata = {
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "tier_id": tier_id,
        "tier_name": tier["name"],
    }

    checkout_request = CheckoutSessionRequest(
        amount=tier["price"],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    # Record pending transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "tier_id": tier_id,
        "amount": tier["price"],
        "currency": "usd",
        "payment_status": "initiated",
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    payment_transactions_col.insert_one(transaction)
    transaction.pop("_id", None)

    return {"url": session.url, "session_id": session.session_id}


@router.get("/checkout/status/{session_id}")
async def check_checkout_status(session_id: str, current_user: dict = Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    # Check if already processed
    existing = payment_transactions_col.find_one({"session_id": session_id}, {"_id": 0})
    if existing and existing.get("payment_status") == "paid":
        return {
            "status": "complete",
            "payment_status": "paid",
            "tier_id": existing.get("tier_id"),
            "already_processed": True,
        }

    host_url = "https://localhost:8001"
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    checkout_status = await stripe_checkout.get_checkout_status(session_id)

    # Update transaction
    update_data = {
        "payment_status": checkout_status.payment_status,
        "status": checkout_status.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if checkout_status.payment_status == "paid":
        # Get tier from transaction
        txn = payment_transactions_col.find_one({"session_id": session_id})
        if txn and txn.get("payment_status") != "paid":
            tier_id = txn.get("tier_id", "scholar")
            users_col.update_one(
                {"id": txn["user_id"]},
                {"$set": {
                    "subscription_tier": tier_id,
                    "subscription_status": "active",
                    "subscribed_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    payment_transactions_col.update_one({"session_id": session_id}, {"$set": update_data})

    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount_total": checkout_status.amount_total,
        "currency": checkout_status.currency,
        "tier_id": existing.get("tier_id") if existing else None,
    }


@router.get("/transactions")
async def list_transactions(current_user: dict = Depends(get_current_user)):
    txns = list(payment_transactions_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(20))
    return txns
