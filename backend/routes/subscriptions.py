from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import os
import uuid
import stripe
from dotenv import load_dotenv
from database import payment_transactions_col, users_col
from middleware import get_current_user

load_dotenv()

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

# Owner/admin emails that always receive top-tier ("elder_circle") access
ADMIN_EMAILS = {
    "hodari@ubuntu-village.org",
    "shy@ubuntu-village.org",
    "quiet927@gmail.com",
}


def _is_admin_email(email: str | None) -> bool:
    """Return True if the email belongs to an admin/owner."""
    if not email:
        return False
    email = email.lower().strip()
    return email in ADMIN_EMAILS or email.endswith("@ubuntu-village.org")

# Membership tiers — amounts defined server-side only
MEMBERSHIP_TIERS = {
    "explorer": {
        "id": "explorer",
        "name": "Explorer",
        "price": 0.0,
        "price_annual": 0.0,
        "description": "Free access to public courses and community",
        "features": ["Browse public courses", "Community access", "Basic archives"],
        "product_ids": {},
    },
    "scholar": {
        "id": "scholar",
        "name": "Scholar",
        "price": 19.99,
        "price_annual": 199.99,
        "description": "Full course enrollment and cohort access",
        "features": ["All Explorer features", "Unlimited course enrollment", "Cohort membership", "Knowledge spaces", "Priority support"],
        "product_ids": {
            "ios_monthly": "com.ileubuntu.scholar.monthly",
            "ios_annual": "com.ileubuntu.scholar.annual",
            "android_monthly": "com.ileubuntu.scholar.monthly",
            "android_annual": "com.ileubuntu.scholar.annual",
        },
    },
    "elder_circle": {
        "id": "elder_circle",
        "name": "Elder Circle",
        "price": 49.99,
        "price_annual": 499.99,
        "description": "Premium access with governance privileges",
        "features": ["All Scholar features", "Live teaching sessions", "Protected archives", "Governance participation", "Custom branding"],
        "product_ids": {
            "ios_monthly": "com.ileubuntu.elder.monthly",
            "ios_annual": "com.ileubuntu.elder.annual",
            "android_monthly": "com.ileubuntu.elder.monthly",
            "android_annual": "com.ileubuntu.elder.annual",
        },
    },
}

# Reverse lookup: product ID → tier ID (for webhook processing)
PRODUCT_ID_TO_TIER = {}
for tid, tinfo in MEMBERSHIP_TIERS.items():
    for _, pid in tinfo.get("product_ids", {}).items():
        PRODUCT_ID_TO_TIER[pid] = tid


@router.get("/tiers")
async def get_tiers():
    return list(MEMBERSHIP_TIERS.values())


@router.get("/my-subscription")
async def get_my_subscription(current_user: dict = Depends(get_current_user)):
    user = users_col.find_one({"id": current_user["id"]}, {"_id": 0})

    # Admin/owner email override — always top tier
    email = (current_user.get("email") or user.get("email") or "").lower()
    if _is_admin_email(email):
        top_tier = "elder_circle"
        limits = {
            "explorer": {"max_enrollments": 2, "cohorts": False, "spaces": False, "live_sessions": False, "restricted_archives": False},
            "scholar": {"max_enrollments": 999999, "cohorts": True, "spaces": True, "live_sessions": False, "restricted_archives": False},
            "elder_circle": {"max_enrollments": 999999, "cohorts": True, "spaces": True, "live_sessions": True, "restricted_archives": True},
        }
        return {
            "tier": top_tier,
            "subscription_status": "active",
            "subscribed_at": user.get("subscribed_at"),
            "is_bypassed": True,
            "enrollment_count": 0,
            "limits": limits[top_tier],
        }

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


@router.post("/activate-mobile")
async def activate_mobile_subscription(request: Request, current_user: dict = Depends(get_current_user)):
    """Called from mobile apps after a successful RevenueCat purchase to sync tier to backend."""
    data = await request.json()
    product_id = data.get("product_id")
    tier_id = data.get("tier_id")
    platform = data.get("platform", "unknown")  # 'ios' or 'android'

    # Resolve tier from product_id or direct tier_id
    resolved_tier = PRODUCT_ID_TO_TIER.get(product_id) or tier_id
    if not resolved_tier or resolved_tier not in MEMBERSHIP_TIERS:
        raise HTTPException(status_code=400, detail="Invalid product or tier")

    users_col.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "subscription_tier": resolved_tier,
            "subscription_status": "active",
            "subscription_platform": platform,
            "subscription_product_id": product_id,
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # Record transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "tier_id": resolved_tier,
        "product_id": product_id,
        "platform": platform,
        "payment_status": "paid",
        "payment_method": "in_app_purchase",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    payment_transactions_col.insert_one(transaction)

    return {"success": True, "tier": resolved_tier}


@router.post("/checkout")
async def create_checkout(request: Request, current_user: dict = Depends(get_current_user)):
    """Web-only Stripe checkout. Mobile apps use RevenueCat + /activate-mobile."""
    data = await request.json()
    tier_id = data.get("tier_id")
    billing_period = data.get("billing_period", "monthly")  # 'monthly' or 'annual'
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

    stripe.api_key = STRIPE_API_KEY

    success_url = f"{origin_url}/subscriptions?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/subscriptions"

    # Determine price based on billing period
    amount = tier["price_annual"] if billing_period == "annual" else tier["price"]

    metadata = {
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "tier_id": tier_id,
        "tier_name": tier["name"],
        "billing_period": billing_period,
    }

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"{tier['name']} — {billing_period.title()}"},
                "unit_amount": int(amount * 100),  # Stripe uses cents
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )

    # Record pending transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.id,
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "tier_id": tier_id,
        "billing_period": billing_period,
        "amount": amount,
        "currency": "usd",
        "payment_status": "initiated",
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    payment_transactions_col.insert_one(transaction)
    transaction.pop("_id", None)

    return {"url": session.url, "session_id": session.id}


@router.get("/checkout/status/{session_id}")
async def check_checkout_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
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

    stripe.api_key = STRIPE_API_KEY
    checkout_session = stripe.checkout.Session.retrieve(session_id)

    payment_status = checkout_session.payment_status or "unpaid"
    session_status = checkout_session.status or "open"

    # Update transaction
    update_data = {
        "payment_status": payment_status,
        "status": session_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if payment_status == "paid":
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
        "status": session_status,
        "payment_status": payment_status,
        "amount_total": checkout_session.amount_total,
        "currency": checkout_session.currency,
        "tier_id": existing.get("tier_id") if existing else None,
    }


@router.get("/transactions")
async def list_transactions(current_user: dict = Depends(get_current_user)):
    txns = list(payment_transactions_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(20))
    return txns
