"""Verified, course-specific RevenueCat access, separate from membership tiers.

A store receipt never comes from the caller. We fetch RevenueCat's current
entitlements for the authenticated Ile Ubuntu user, then reconcile only the
explicitly mapped course. Revocation preserves progress and unrelated grants.
"""

import os
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from uuid import uuid4
from pymongo.errors import DuplicateKeyError

import httpx
from fastapi import HTTPException
from database import courses_col, enrollments_col, users_col

STORES = {"ios": "app_store", "android": "play_store"}


def api_key():
    return (
        os.environ.get("REVENUECAT_COURSE_API_KEY")
        or os.environ.get("REVENUECAT_SECRET_KEY")
        or ""
    ).strip()


def configured():
    return bool(api_key())


def mapping(course):
    value = course.get("iap") or {}
    if not isinstance(value, dict):
        return {}
    return value


def fetch_subscriber(user_id):
    key = api_key()
    if not key:
        raise HTTPException(503, "Course purchase verification is not available yet")
    try:
        response = httpx.get(
            "https://api.revenuecat.com/v1/subscribers/" + quote(user_id, safe=""),
            headers={"Authorization": "Bearer " + key},
            timeout=20,
        )
        if response.status_code == 404:
            return {"entitlements": {}, "non_subscriptions": {}}
        response.raise_for_status()
        result = response.json()["subscriber"]
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("entitlements"), dict)
            or not isinstance(result.get("non_subscriptions"), dict)
        ):
            raise ValueError("Invalid subscriber")
        return result
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        # Do not revoke access on an unavailable or malformed upstream response.
        raise HTTPException(
            503, "We couldn't confirm your purchase. Please try again."
        ) from exc


def allowed_sandbox(user_id):
    return user_id in {
        x.strip()
        for x in os.environ.get("REVENUECAT_SANDBOX_USER_IDS", "").split(",")
        if x.strip()
    }


def verified_grant(course, subscriber, user_id):
    config = mapping(course)
    entitlement = subscriber.get("entitlements", {}).get(config.get("entitlement_id"))
    if not isinstance(entitlement, dict) or entitlement.get("expires_date") is not None:
        return None
    product = entitlement.get("product_identifier")
    stores = {
        store
        for platform, store in STORES.items()
        if config.get(platform + "_product_id") == product
    }
    if not product or not stores or not entitlement.get("purchase_date"):
        return None
    # Entitlements alone could be a promotion or a subscription. Require a real,
    # non-refunded one-time purchase in the correct store and environment too.
    receipts = subscriber.get("non_subscriptions", {}).get(product, [])
    valid = [
        r
        for r in receipts
        if isinstance(r, dict)
        and r.get("store") in stores
        and r.get("id")
        and r.get("purchase_date") == entitlement["purchase_date"]
        and not r.get("refunded_at")
        and (
            r.get("is_sandbox") is False
            or (r.get("is_sandbox") is True and allowed_sandbox(user_id))
        )
    ]
    if not valid:
        return None
    receipt = valid[-1]
    return {
        "product_id": product,
        "receipt_id": str(receipt["id"]),
        "store": receipt["store"],
        "sandbox": receipt["is_sandbox"],
        "purchased_at": receipt["purchase_date"],
    }


def reconcile_course(course, user_id, subscriber):
    """Only enrollments created by this integration can be revoked by it."""
    cid = course["id"]
    grant = verified_grant(course, subscriber, user_id)
    current = enrollments_col.find_one({"course_id": cid, "user_id": user_id})
    now = datetime.now(timezone.utc)
    if grant:
        # Reconciliation is idempotent; the unique user/course grant index is
        # independent of a restore or webhook retry. No Stripe earnings ledger
        # entry is created: store proceeds require separate settlement.
        from database import course_iap_grants_col

        course_iap_grants_col.update_one(
            {"course_id": cid, "user_id": user_id},
            {
                "$set": {**grant, "active": True, "verified_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        if not current:
            buyer = users_col.find_one({"id": user_id})
            if not buyer:
                return {"enrolled": False, "verified": False}
            try:
                inserted = enrollments_col.update_one(
                    {"user_id": user_id, "course_id": cid},
                    {
                        "$setOnInsert": {
                            "id": str(uuid4()),
                            "user_name": buyer.get("name", ""),
                            "enrolled_at": now,
                            "completed_lessons": [],
                            "progress": 0.0,
                            "status": "active",
                            "completed_at": None,
                            "via_purchase": True,
                            "source": "revenuecat",
                            "iap_managed": True,
                        }
                    },
                    upsert=True,
                )
            except DuplicateKeyError:
                inserted = None
            if inserted and inserted.upserted_id:
                courses_col.update_one({"id": cid}, {"$inc": {"enrolled_count": 1}})
        # Preserve staff imports, web purchases, progress, and access overrides.
        enrollments_col.update_one(
            {"user_id": user_id, "course_id": cid, "iap_managed": True},
            {"$unset": {"iap_revoked_at": ""}, "$set": {"iap_verified_at": now}},
        )
        return {"enrolled": True, "verified": True}
    from database import course_iap_grants_col

    course_iap_grants_col.update_one(
        {"course_id": cid, "user_id": user_id},
        {"$set": {"active": False, "verified_at": now}},
    )
    if current and current.get("iap_managed"):
        enrollments_col.update_one(
            {"id": current["id"], "iap_managed": True},
            {"$set": {"iap_revoked_at": now}},
        )
        return {"enrolled": False, "verified": False}
    return {"enrolled": bool(current), "verified": False}


def reconcile_user(user_id, course_id=None):
    from database import course_iap_sync_col
    from pymongo import ReturnDocument

    now = datetime.now(timezone.utc)
    token = str(uuid4())
    try:
        course_iap_sync_col.find_one_and_update(
            {"user_id": user_id, "expires_at": {"$lte": now}},
            {"$set": {"token": token, "expires_at": now + timedelta(minutes=5)}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            503, "A purchase confirmation is already in progress. Please try again."
        ) from exc
    try:
        subscriber = fetch_subscriber(user_id)
        query = {"iap.entitlement_id": {"$exists": True}}
        if course_id:
            query["id"] = course_id
        return {
            c["id"]: reconcile_course(c, user_id, subscriber)
            for c in courses_col.find(query)
        }
    finally:
        course_iap_sync_col.delete_one({"user_id": user_id, "token": token})


def handle_course_event(event):
    """Re-read current state so duplicate/out-of-order refund events are safe."""
    if event.get("type") == "TRANSFER":
        ids = set(
            (event.get("transferred_from") or []) + (event.get("transferred_to") or [])
        )
        for uid in ids:
            if users_col.find_one({"id": uid}):
                reconcile_user(uid)
        return True
    product_id = event.get("product_id")
    course = (
        courses_col.find_one(
            {
                "$or": [
                    {"iap.ios_product_id": product_id},
                    {"iap.android_product_id": product_id},
                ]
            }
        )
        if product_id
        else None
    )
    if not course:
        return False
    if event.get("type") not in {
        "NON_RENEWING_PURCHASE",
        "CANCELLATION",
        "EXPIRATION",
        "UNCANCELLATION",
    }:
        return True
    if event.get("environment") == "SANDBOX" and not allowed_sandbox(
        event.get("app_user_id")
    ):
        return True
    if event.get("id"):
        from database import course_iap_events_col

        fields = {
            key: event.get(key)
            for key in (
                "type",
                "product_id",
                "transaction_id",
                "store",
                "environment",
                "price",
                "price_in_purchased_currency",
                "currency",
                "commission_percentage",
                "tax_percentage",
                "event_timestamp_ms",
                "purchased_at_ms",
                "cancel_reason",
            )
        }
        course_iap_events_col.update_one(
            {"event_id": event["id"]},
            {
                "$setOnInsert": {
                    **fields,
                    "course_id": course["id"],
                    "teacher_id": course.get("instructor_id"),
                    "user_id": event.get("app_user_id"),
                    "payout_status": "not_scheduled",
                    "recorded_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    uid = event.get("app_user_id")
    if uid and users_col.find_one({"id": uid}):
        reconcile_user(uid, course["id"])
    return True
