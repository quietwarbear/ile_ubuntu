"""Real reconciliation and authenticated HTTP routes, with isolated Mongo data."""

import os
import sys
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import mongomock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import database
import course_iap as service
import course_access
from routes import course_iap as routes
from routes import revenuecat_webhook as webhook
from routes import quizzes, courses, marketplace
from middleware import get_current_user

REAL_FETCH = service.fetch_subscriber

COURSE = {
    "id": "course",
    "instructor_id": "teacher",
    "status": "active",
    "is_premium": True,
    "premium_price": 3,
    "iap": {
        "enabled": True,
        "entitlement_id": "course_access",
        "ios_product_id": "ios.course",
        "android_product_id": "android.course",
    },
}
PURCHASE_DATE = "2026-11-06T12:00:00Z"
SUBSCRIBER = {
    "entitlements": {
        "course_access": {
            "product_identifier": "ios.course",
            "purchase_date": PURCHASE_DATE,
            "expires_date": None,
        }
    },
    "non_subscriptions": {
        "ios.course": [
            {
                "id": "receipt",
                "store": "app_store",
                "purchase_date": PURCHASE_DATE,
                "is_sandbox": False,
            }
        ]
    },
}


@pytest.fixture
def db(monkeypatch):
    mdb = mongomock.MongoClient(tz_aware=True).test
    for mod in (database, service, routes, webhook, quizzes, courses, marketplace):
        for name, value in list(vars(mod).items()):
            if name.endswith("_col") and hasattr(value, "name"):
                monkeypatch.setattr(mod, name, mdb[value.name])
    mdb.course_iap_grants.create_index([("course_id", 1), ("user_id", 1)], unique=True)
    mdb.course_iap_events.create_index("event_id", unique=True)
    mdb.course_iap_sync.create_index("user_id", unique=True)
    mdb.enrollments.create_index(
        [("user_id", 1), ("course_id", 1)],
        unique=True,
        partialFilterExpression={"iap_managed": True},
    )
    mdb.courses.insert_one(deepcopy(COURSE))
    mdb.users.insert_one(
        {
            "id": "learner",
            "name": "Learner",
            "role": "student",
            "subscription_tier": "scholar",
        }
    )
    monkeypatch.setenv("REVENUECAT_COURSE_API_KEY", "server-test-key")
    monkeypatch.delenv("REVENUECAT_SANDBOX_USER_IDS", raising=False)
    monkeypatch.setattr(service, "fetch_subscriber", lambda uid: deepcopy(SUBSCRIBER))
    monkeypatch.setattr(webhook, "emit", lambda *a, **k: None)
    monkeypatch.setattr(webhook, "REVENUECAT_WEBHOOK_SECRET", "webhook-test-secret")
    return mdb


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(routes.router)
    app.include_router(webhook.router)
    app.include_router(quizzes.router)
    app.include_router(courses.router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "learner",
        "role": "student",
    }
    return TestClient(app)


def test_store_purchase_does_not_require_membership_and_is_idempotent(db):
    for _ in range(2):
        assert service.reconcile_user("learner", "course")["course"]["verified"]
    assert db.enrollments.count_documents({}) == 1
    assert db.courses.find_one({"id": "course"})["enrolled_count"] == 1
    assert db.users.find_one({"id": "learner"})["subscription_tier"] == "scholar"
    assert db.payment_transactions.count_documents({}) == 0


def test_refund_revokes_access_preserves_progress_and_restore_reopens(db, monkeypatch):
    service.reconcile_user("learner", "course")
    db.enrollments.update_one(
        {},
        {
            "$set": {
                "progress": 80,
                "completed_lessons": ["lesson"],
                "access_ends_at": None,
            }
        },
    )
    monkeypatch.setattr(
        service,
        "fetch_subscriber",
        lambda uid: {"entitlements": {}, "non_subscriptions": {}},
    )
    assert not service.reconcile_user("learner", "course")["course"]["enrolled"]
    enrollment = db.enrollments.find_one({})
    assert enrollment["progress"] == 80
    with pytest.raises(HTTPException):
        course_access.require_open(COURSE, enrollment)
    monkeypatch.setattr(service, "fetch_subscriber", lambda uid: deepcopy(SUBSCRIBER))
    assert service.reconcile_user("learner", "course")["course"]["enrolled"]
    enrollment = db.enrollments.find_one({})
    course_access.require_open(COURSE, enrollment)
    assert enrollment["progress"] == 80 and enrollment["access_ends_at"] is None


@pytest.mark.parametrize("source", ["stripe", "import"])
def test_unrelated_enrollment_survives_course_refund(db, monkeypatch, source):
    db.enrollments.insert_one(
        {
            "id": "enrollment",
            "course_id": "course",
            "user_id": "learner",
            "source": source,
            "progress": 90,
        }
    )
    service.reconcile_user("learner", "course")
    monkeypatch.setattr(
        service,
        "fetch_subscriber",
        lambda uid: {"entitlements": {}, "non_subscriptions": {}},
    )
    service.reconcile_user("learner", "course")
    assert db.enrollments.find_one({}) == {
        "_id": db.enrollments.find_one({})["_id"],
        "id": "enrollment",
        "course_id": "course",
        "user_id": "learner",
        "source": source,
        "progress": 90,
    }


@pytest.mark.parametrize(
    "change",
    ["sandbox", "wrong_store", "wrong_product", "expired", "refunded", "promotional"],
)
def test_unverified_receipts_cannot_unlock(db, change):
    sub = deepcopy(SUBSCRIBER)
    receipt = sub["non_subscriptions"]["ios.course"][0]
    if change == "sandbox":
        receipt["is_sandbox"] = True
    if change == "wrong_store":
        receipt["store"] = "play_store"
    if change == "wrong_product":
        sub["entitlements"]["course_access"]["product_identifier"] = "other.course"
    if change == "expired":
        sub["entitlements"]["course_access"]["expires_date"] = "2026-01-01T00:00:00Z"
    if change == "refunded":
        receipt["refunded_at"] = "2026-11-06T13:00:00Z"
    if change == "promotional":
        sub["non_subscriptions"] = {}
    assert service.verified_grant(COURSE, sub, "learner") is None


def test_sandbox_is_only_available_to_explicit_test_accounts(db, monkeypatch):
    sub = deepcopy(SUBSCRIBER)
    sub["non_subscriptions"]["ios.course"][0]["is_sandbox"] = True
    monkeypatch.setenv("REVENUECAT_SANDBOX_USER_IDS", "learner")
    assert service.verified_grant(COURSE, sub, "learner")
    assert service.verified_grant(COURSE, sub, "other") is None


def test_client_cannot_choose_purchase_owner_or_fake_receipt(client, db, monkeypatch):
    monkeypatch.setattr(
        service,
        "fetch_subscriber",
        lambda uid: {"entitlements": {}, "non_subscriptions": {}},
    )
    result = client.post(
        "/api/courses/course/confirm-purchase",
        json={"user_id": "paid-user", "receipt": "fake", "verified": True},
    )
    assert result.status_code == 200 and not result.json()["enrolled"]
    assert db.enrollments.count_documents({}) == 0


def test_missing_api_key_and_upstream_failure_never_revoke_paid_access(db, monkeypatch):
    service.reconcile_user("learner", "course")
    # Fetch function itself fails closed without credentials (no outbound call).
    monkeypatch.delenv("REVENUECAT_COURSE_API_KEY", raising=False)
    monkeypatch.delenv("REVENUECAT_SECRET_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        REAL_FETCH("learner")
    assert exc.value.status_code == 503
    assert db.enrollments.find_one({}).get("iap_revoked_at") is None


def test_webhook_requires_authorization(client, db):
    assert client.post("/api/webhook/revenuecat", json={"event": {}}).status_code == 401
    assert db.enrollments.count_documents({}) == 0


def test_refund_event_never_cancels_membership_and_current_provider_state_wins(
    client, db
):
    event = {
        "id": "event1",
        "type": "CANCELLATION",
        "app_user_id": "learner",
        "product_id": "ios.course",
        "environment": "PRODUCTION",
        "store": "APP_STORE",
        "transaction_id": "t1",
    }
    for _ in range(2):
        result = client.post(
            "/api/webhook/revenuecat",
            headers={"Authorization": "Bearer webhook-test-secret"},
            json={"event": event},
        )
        assert result.status_code == 200
    assert db.users.find_one({"id": "learner"})["subscription_tier"] == "scholar"
    assert db.enrollments.count_documents({}) == 1
    assert db.course_iap_events.count_documents({}) == 1
    assert db.course_iap_events.find_one({})["payout_status"] == "not_scheduled"


def test_unmapped_cancellation_cannot_downgrade_member(client, db):
    result = client.post(
        "/api/webhook/revenuecat",
        headers={"Authorization": "webhook-test-secret"},
        json={
            "event": {
                "type": "CANCELLATION",
                "app_user_id": "learner",
                "product_id": "unknown",
            }
        },
    )
    assert result.json()["status"] == "ignored"
    assert db.users.find_one({"id": "learner"})["subscription_tier"] == "scholar"


def test_transfer_rechecks_both_accounts(db, monkeypatch):
    service.reconcile_user("learner", "course")
    db.users.insert_one({"id": "recipient"})
    monkeypatch.setattr(
        service,
        "fetch_subscriber",
        lambda uid: (
            deepcopy(SUBSCRIBER)
            if uid == "recipient"
            else {"entitlements": {}, "non_subscriptions": {}}
        ),
    )
    assert service.handle_course_event(
        {
            "type": "TRANSFER",
            "transferred_from": ["learner"],
            "transferred_to": ["recipient"],
        }
    )
    assert db.enrollments.find_one({"user_id": "learner"})["iap_revoked_at"]
    assert (
        db.enrollments.find_one({"user_id": "recipient"}).get("iap_revoked_at") is None
    )


def test_educator_cannot_map_someone_elses_store_product(client):
    response = client.put(
        "/api/courses/course/purchase-options", json={"enabled": True}
    )
    assert response.status_code == 403


def test_quiz_reading_enforces_paid_access_and_refund_revocation(client, db):
    db.lessons.insert_one({"id": "lesson", "course_id": "course"})
    db.quizzes.insert_one(
        {
            "id": "quiz",
            "lesson_id": "lesson",
            "questions": [{"id": "q", "correct_answer": "secret"}],
        }
    )
    url = "/api/courses/course/lessons/lesson/quiz"
    assert client.get(url).status_code == 403
    service.reconcile_user("learner", "course")
    assert client.get(url).json()["questions"] == [{"id": "q"}]
    db.enrollments.update_one(
        {}, {"$set": {"iap_revoked_at": datetime.now(timezone.utc)}}
    )
    assert client.get(url).status_code == 403


def test_overlapping_confirmation_cannot_overwrite_newer_verification(db):
    from datetime import timedelta

    db.course_iap_sync.insert_one(
        {
            "user_id": "learner",
            "token": "other",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=1),
        }
    )
    with pytest.raises(HTTPException) as exc:
        service.reconcile_user("learner", "course")
    assert exc.value.status_code == 503
    assert db.enrollments.count_documents({}) == 0


def test_web_purchase_after_store_refund_keeps_progress_and_is_independent(
    client, db, monkeypatch
):
    service.reconcile_user("learner", "course")
    db.enrollments.update_one(
        {}, {"$set": {"progress": 80, "iap_revoked_at": datetime.now(timezone.utc)}}
    )
    # Website enrollment still reaches the premium checkout trigger.
    response = client.post("/api/courses/course/enroll")
    assert (
        response.status_code == 402
        and response.json()["detail"] == "premium_required:3"
    )
    db.payment_transactions.insert_one(
        {
            "id": "paid",
            "session_id": "stripe-session",
            "type": "course_purchase",
            "payment_status": "pending",
            "user_id": "learner",
            "course_id": "course",
            "teacher_id": "teacher",
            "amount": 3,
        }
    )
    monkeypatch.setattr(marketplace, "emit", lambda *a, **k: None)
    assert marketplace.fulfill_course_purchase({"id": "stripe-session"})
    assert db.enrollments.find_one({})["progress"] == 80
    assert db.enrollments.find_one({})["source"] == "stripe"
    monkeypatch.setattr(
        service,
        "fetch_subscriber",
        lambda uid: {"entitlements": {}, "non_subscriptions": {}},
    )
    assert service.reconcile_user("learner", "course")["course"]["enrolled"]


def test_existing_server_secret_can_verify_courses(db, monkeypatch):
    monkeypatch.delenv("REVENUECAT_COURSE_API_KEY", raising=False)
    monkeypatch.setenv("REVENUECAT_SECRET_KEY", "existing-backend-key")
    assert service.configured() and service.api_key() == "existing-backend-key"
