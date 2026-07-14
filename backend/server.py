import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API docs are disabled by default in production. Set ENABLE_API_DOCS=true to expose
# /docs and /openapi.json (e.g. in local development).
_DOCS_ENABLED = os.environ.get("ENABLE_API_DOCS", "").strip().lower() in ("1", "true", "yes")

app = FastAPI(
    title="The Ile Ubuntu API",
    version="2.0.0",
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)

# Explicit CORS allow-list (wildcard + credentials is invalid per the CORS spec).
# Override/extend with a comma-separated CORS_ORIGINS env var.
_DEFAULT_CORS_ORIGINS = [
    "https://ile-ubuntu.org",
    "https://www.ile-ubuntu.org",
    # Capacitor native shells
    "capacitor://localhost",
    "https://localhost",
    "ionic://localhost",
    # Local development
    "http://localhost:3000",
    "http://localhost:8001",
]
_env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
CORS_ORIGINS = _env_origins or _DEFAULT_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _ensure_indexes():
    from database import ensure_indexes
    ensure_indexes()

# Ensure uploads directory exists
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Import and register routers
from routes.auth import router as auth_router
from routes.courses import router as courses_router
from routes.cohorts import router as cohorts_router
from routes.community import router as community_router
from routes.archives import router as archives_router
from routes.files import router as files_router
from routes.messages import router as messages_router
from routes.enrollments import router as enrollments_router
from routes.live_sessions import router as live_sessions_router
from routes.google_integration import router as google_router
from routes.spaces import router as spaces_router
from routes.analytics import router as analytics_router
from routes.search import router as search_router
from routes.subscriptions import router as subscriptions_router
from routes.email_notifications import router as email_router
from routes.session_records import router as session_records_router
from routes.certificates import router as certificates_router
from routes.push_notifications import router as push_router
from routes.blog import router as blog_router
from routes.revenuecat_webhook import router as revenuecat_router
from routes.quizzes import router as quizzes_router
from routes.lesson_comments import router as lesson_comments_router
from routes.events import router as events_router
from routes.marketplace import router as marketplace_router
from routes.family import router as family_router
from routes.learning_circles import router as learning_circles_router
from routes.community_dashboard import router as community_dashboard_router
from routes.checkins import router as checkins_router
from routes.villages import router as villages_router
from routes.portfolio import router as portfolio_router
from routes.guide import router as guide_router

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(cohorts_router)
app.include_router(community_router)
app.include_router(archives_router)
app.include_router(files_router)
app.include_router(messages_router)
app.include_router(enrollments_router)
app.include_router(live_sessions_router)
app.include_router(google_router)
app.include_router(spaces_router)
app.include_router(analytics_router)
app.include_router(search_router)
app.include_router(subscriptions_router)
app.include_router(email_router)
app.include_router(session_records_router)
app.include_router(certificates_router)
app.include_router(push_router)
app.include_router(blog_router)
app.include_router(revenuecat_router)
app.include_router(quizzes_router)
app.include_router(lesson_comments_router)
app.include_router(events_router)
app.include_router(marketplace_router)
app.include_router(family_router)
app.include_router(learning_circles_router)
app.include_router(community_dashboard_router)
app.include_router(checkins_router)
app.include_router(villages_router)
app.include_router(portfolio_router)
app.include_router(guide_router)


@app.get("/")
async def root():
    return {"message": "The Ile Ubuntu API v2.0"}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    import os
    import stripe as stripe_lib
    from database import payment_transactions_col, users_col
    from datetime import datetime, timezone

    body = await request.body()
    stripe_signature = request.headers.get("Stripe-Signature")

    # strip(): paste artifacts (trailing comma/space) break Stripe auth.
    api_key = (os.environ.get("STRIPE_API_KEY") or "").strip(" ,\n\t\r")
    webhook_secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip(" ,\n\t\r")
    if not api_key:
        return {"status": "error", "message": "Stripe not configured"}

    # Fail closed: never process unverified webhook payloads on a payments endpoint.
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")
    if not stripe_signature:
        raise HTTPException(status_code=401, detail="Missing Stripe-Signature header")

    stripe_lib.api_key = api_key

    try:
        stripe_lib.Webhook.construct_event(body, stripe_signature, webhook_secret)
        # Signature verified — parse the raw payload ourselves. stripe v15's
        # Event object no longer behaves like a dict (.get raises
        # AttributeError). Same fix as routes/marketplace.py.
        import json as _json
        event = _json.loads(body)

        if event.get("type") == "checkout.session.completed":
            session_data = event["data"]["object"]
            session_id = session_data["id"]
            payment_status = session_data.get("payment_status", "unpaid")

            # Premium course purchases (Teacher Marketplace) fulfill separately
            if payment_status == "paid" and (session_data.get("metadata") or {}).get("kind") == "course_purchase":
                from routes.marketplace import fulfill_course_purchase
                fulfill_course_purchase(session_data)
                return {"status": "ok"}

            if payment_status == "paid":
                txn = payment_transactions_col.find_one({"session_id": session_id})
                if txn and txn.get("payment_status") != "paid":
                    payment_transactions_col.update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "payment_status": "paid",
                            "status": "complete",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    tier_id = txn.get("tier_id", "scholar")
                    users_col.update_one(
                        {"id": txn["user_id"]},
                        {"$set": {
                            "subscription_tier": tier_id,
                            "subscription_status": "active",
                            "subscribed_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    from events import emit
                    emit("subscription.activated", {"id": txn["user_id"]},
                         meta={"tier": tier_id, "provider": "stripe"})

        return {"status": "ok"}
    except Exception as e:
        # Non-2xx so Stripe retries legitimate deliveries and rejects bad signatures.
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
