from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="The Ile Ubuntu API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
async def root():
    return {"message": "The Ile Ubuntu API v2.0"}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    import os
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    from database import payment_transactions_col, users_col
    from datetime import datetime, timezone

    body = await request.body()
    stripe_signature = request.headers.get("Stripe-Signature")

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "Stripe not configured"}

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    try:
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)

        if webhook_response.payment_status == "paid":
            txn = payment_transactions_col.find_one({"session_id": webhook_response.session_id})
            if txn and txn.get("payment_status") != "paid":
                payment_transactions_col.update_one(
                    {"session_id": webhook_response.session_id},
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

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
