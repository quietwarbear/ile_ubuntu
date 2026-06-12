"""Teacher Marketplace — Stripe Connect (Express) for premium course sales.

Money flow: student pays via Stripe Checkout on the WEB ONLY (Apple/Google
in-app purchase rules prohibit Stripe checkout for digital goods inside the
native apps). The charge is a destination charge: funds land on the teacher's
connected Express account, the platform keeps MARKETPLACE_FEE_PCT as an
application fee. Fulfillment (enrollment) happens in the Stripe webhook in
server.py, never in the redirect, so a forged success URL can't grant access.
"""

import os
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from database import users_col, courses_col, enrollments_col, payment_transactions_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from events import emit

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

# The marketplace runs on its OWN Stripe account (Connect-enabled), separate
# from the subscriptions account. Falls back to STRIPE_API_KEY for
# single-account setups. IMPORTANT: every Stripe call below passes api_key
# explicitly — never set stripe.api_key globally here, the subscriptions code
# owns that global and handlers run concurrently.
MARKETPLACE_KEY = os.environ.get("STRIPE_MARKETPLACE_API_KEY", "") or os.environ.get("STRIPE_API_KEY", "")
MARKETPLACE_WEBHOOK_SECRET = os.environ.get("STRIPE_MARKETPLACE_WEBHOOK_SECRET", "")
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.ile-ubuntu.org").rstrip("/")

# Platform fee — 15% per the marketing copy; override with MARKETPLACE_FEE_PCT.
FEE_PCT = float(os.environ.get("MARKETPLACE_FEE_PCT", "0.15"))

MAX_COURSE_PRICE = 999.0

_ALLOWED_REDIRECT_ORIGINS = {
    PUBLIC_SITE_URL,
    "https://ile-ubuntu.org",
    "https://www.ile-ubuntu.org",
    "http://localhost:3000",
}


def _require_stripe():
    if not MARKETPLACE_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured")


def _client() -> "stripe.StripeClient":
    """Scoped client for the marketplace account (stripe-python v15 style).
    The classic module-level resource API misbehaves with per-call api_key
    under v15 — always go through this client."""
    _require_stripe()
    return stripe.StripeClient(MARKETPLACE_KEY)


def _require_faculty(user: dict):
    if not has_permission(user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Faculty access required")


def _validate_redirect(url: str, fallback_path: str) -> str:
    """Only allow redirects back to our own origins."""
    if url and any(url.startswith(origin + "/") or url == origin for origin in _ALLOWED_REDIRECT_ORIGINS):
        return url
    return f"{PUBLIC_SITE_URL}{fallback_path}"


# --- Connect onboarding ---

@router.get("/connect/status")
def connect_status(current_user: dict = Depends(get_current_user)):
    _require_faculty(current_user)
    account_id = current_user.get("stripe_account_id")
    if not account_id:
        return {"connected": False, "charges_enabled": False, "payouts_enabled": False}
    try:
        # Direct HTTPS call — the stripe SDK's GET path misbehaves in this
        # deploy environment (POSTs work); requests is proven in prod here.
        import requests as _requests
        resp = _requests.get(
            f"https://api.stripe.com/v1/accounts/{account_id}",
            auth=(MARKETPLACE_KEY, ""),
            timeout=20,
        )
        body = resp.json()
        if resp.status_code >= 400:
            msg = (body.get("error") or {}).get("message", f"HTTP {resp.status_code}")
            return {"connected": True, "charges_enabled": False, "payouts_enabled": False,
                    "status_error": msg}
        return {
            "connected": True,
            "charges_enabled": bool(body.get("charges_enabled")),
            "payouts_enabled": bool(body.get("payouts_enabled")),
            "details_submitted": bool(body.get("details_submitted")),
        }
    except Exception as e:
        # Status is informational — degrade with the reason, never 500.
        import logging
        logging.getLogger(__name__).exception("connect_status failed for %s", account_id)
        return {
            "connected": True,
            "charges_enabled": False,
            "payouts_enabled": False,
            "status_error": f"{type(e).__name__}: {e}",
        }


@router.post("/connect/onboard")
async def connect_onboard(request: Request, current_user: dict = Depends(get_current_user)):
    """Create (or reuse) the teacher's Express account and return an onboarding link."""
    _require_faculty(current_user)
    _require_stripe()
    data = await request.json()
    return_url = _validate_redirect(data.get("return_url", ""), "/teacher-dashboard")
    refresh_url = _validate_redirect(data.get("refresh_url", ""), "/teacher-dashboard")

    account_id = current_user.get("stripe_account_id")
    try:
        client = _client()
        if not account_id:
            acct = client.v1.accounts.create(params={
                "type": "express",
                "email": current_user.get("email"),
                "capabilities": {
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                "metadata": {"user_id": current_user["id"]},
            })
            account_id = acct["id"]
            users_col.update_one({"id": current_user["id"]}, {"$set": {"stripe_account_id": account_id}})

        link = client.v1.account_links.create(params={
            "account": account_id,
            "refresh_url": refresh_url,
            "return_url": return_url,
            "type": "account_onboarding",
        })
        return {"url": link["url"]}
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")


@router.get("/connect/dashboard-link")
def connect_dashboard_link(current_user: dict = Depends(get_current_user)):
    _require_faculty(current_user)
    account_id = current_user.get("stripe_account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="No connected Stripe account")
    _require_stripe()
    # v15's StripeClient has no login-link service; hit the endpoint directly.
    import requests as _requests
    resp = _requests.post(
        f"https://api.stripe.com/v1/accounts/{account_id}/login_links",
        auth=(MARKETPLACE_KEY, ""),
        timeout=20,
    )
    body = resp.json()
    if resp.status_code >= 400:
        msg = (body.get("error") or {}).get("message", "Stripe error")
        raise HTTPException(status_code=502, detail=f"Stripe error: {msg}")
    return {"url": body["url"]}


# --- Premium pricing ---

@router.post("/courses/{course_id}/set-premium")
async def set_premium(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    _require_faculty(current_user)
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only the course instructor can set pricing")

    data = await request.json()
    try:
        price = round(float(data.get("price", 0)), 2)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid price")
    if price < 0 or price > MAX_COURSE_PRICE:
        raise HTTPException(status_code=400, detail=f"Price must be between 0 and {MAX_COURSE_PRICE}")

    if price > 0:
        # Can't sell without a payments-enabled account.
        status = connect_status(current_user)
        if not status.get("charges_enabled"):
            raise HTTPException(status_code=400, detail="Complete Stripe onboarding before setting a price")

    courses_col.update_one(
        {"id": course_id},
        {"$set": {"is_premium": price > 0, "premium_price": price}},
    )
    return {"success": True, "is_premium": price > 0, "premium_price": price}


# --- Checkout (web only — native apps must not reach this; see frontend guard) ---

@router.post("/courses/{course_id}/checkout")
async def course_checkout(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    _require_stripe()
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    price = course.get("premium_price") or 0
    if not course.get("is_premium") or price <= 0:
        raise HTTPException(status_code=400, detail="This course is not a premium course")

    if enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id}):
        raise HTTPException(status_code=400, detail="Already enrolled")

    teacher = users_col.find_one({"id": course["instructor_id"]}) or {}
    teacher_account = teacher.get("stripe_account_id")
    if not teacher_account:
        raise HTTPException(status_code=400, detail="This teacher cannot accept payments yet")

    data = await request.json()
    success_url = _validate_redirect(data.get("success_url", ""), f"/courses/{course_id}")
    cancel_url = _validate_redirect(data.get("cancel_url", ""), f"/courses/{course_id}")

    amount_cents = int(round(price * 100))
    fee_cents = int(round(amount_cents * FEE_PCT))

    try:
        session = _client().v1.checkout.sessions.create(params={
            "mode": "payment",
            "line_items": [{
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {"name": course["title"], "description": "Premium course — The Ile Ubuntu"},
                },
            }],
            "payment_intent_data": {
                "application_fee_amount": fee_cents,
                "transfer_data": {"destination": teacher_account},
            },
            "customer_email": current_user.get("email"),
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "kind": "course_purchase",
                "course_id": course_id,
                "user_id": current_user["id"],
                "teacher_id": course["instructor_id"],
            },
        })
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")

    payment_transactions_col.insert_one({
        "id": str(uuid.uuid4()),
        "type": "course_purchase",
        "session_id": session["id"],
        "course_id": course_id,
        "course_title": course["title"],
        "user_id": current_user["id"],
        "user_email": current_user.get("email", ""),
        "teacher_id": course["instructor_id"],
        "amount": price,
        "platform_fee": round(fee_cents / 100, 2),
        "teacher_earnings": round((amount_cents - fee_cents) / 100, 2),
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session["url"]}


def fulfill_course_purchase(session_data: dict) -> bool:
    """Called from the Stripe webhook on checkout.session.completed.
    Marks the transaction paid and enrolls the buyer. Idempotent."""
    session_id = session_data["id"]
    txn = payment_transactions_col.find_one({"session_id": session_id, "type": "course_purchase"})
    if not txn or txn.get("payment_status") == "paid":
        return False

    payment_transactions_col.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}},
    )

    if not enrollments_col.find_one({"user_id": txn["user_id"], "course_id": txn["course_id"]}):
        buyer = users_col.find_one({"id": txn["user_id"]}) or {}
        enrollments_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": txn["user_id"],
            "user_name": buyer.get("name", ""),
            "course_id": txn["course_id"],
            "enrolled_at": datetime.now(timezone.utc),
            "completed_lessons": [],
            "progress": 0.0,
            "status": "active",
            "completed_at": None,
            "via_purchase": True,
        })
        courses_col.update_one({"id": txn["course_id"]}, {"$inc": {"enrolled_count": 1}})

    emit("course.purchased", {"id": txn["user_id"]}, "course", txn["course_id"],
         meta={"amount": txn["amount"], "teacher_id": txn["teacher_id"]})
    emit("course.enrolled", {"id": txn["user_id"]}, "course", txn["course_id"], meta={"via": "purchase"})
    return True


# --- Webhook (configure on the MARKETPLACE Stripe account) ---

@router.post("/webhook")
async def marketplace_webhook(request: Request):
    """checkout.session.completed from the marketplace Stripe account.

    Fail closed: requires STRIPE_MARKETPLACE_WEBHOOK_SECRET and a valid
    signature. Configure the endpoint on the marketplace account pointing to
    /api/marketplace/webhook with the checkout.session.completed event.
    """
    if not MARKETPLACE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Marketplace webhook secret not configured")
    signature = request.headers.get("Stripe-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Stripe-Signature header")

    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, signature, MARKETPLACE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event.get("type") == "checkout.session.completed":
        session_data = event["data"]["object"]
        if session_data.get("payment_status") == "paid" and \
                (session_data.get("metadata") or {}).get("kind") == "course_purchase":
            fulfill_course_purchase(session_data)

    return {"status": "ok"}


# --- Earnings ---

@router.get("/earnings")
def earnings(current_user: dict = Depends(get_current_user)):
    _require_faculty(current_user)
    txns = list(payment_transactions_col.find(
        {"type": "course_purchase", "teacher_id": current_user["id"], "payment_status": "paid"},
        {"_id": 0},
    ).sort("created_at", -1))

    total_gross = sum(t.get("amount", 0) for t in txns)
    total_fees = sum(t.get("platform_fee", 0) for t in txns)
    by_course = {}
    for t in txns:
        c = by_course.setdefault(t["course_id"], {"course_id": t["course_id"], "course_title": t.get("course_title", ""), "total_sales": 0, "net_earnings": 0.0})
        c["total_sales"] += 1
        c["net_earnings"] += t.get("teacher_earnings", 0)

    return {
        "summary": {
            "total_sales": len(txns),
            "total_gross": round(total_gross, 2),
            "total_fees": round(total_fees, 2),
            "total_net": round(total_gross - total_fees, 2),
        },
        "by_course": list(by_course.values()),
        "recent_transactions": txns[:20],
    }
