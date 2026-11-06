"""App-store course purchase options and server-verified restore/confirmation."""

from fastapi import APIRouter, Depends, HTTPException, Request
from middleware import get_current_user
from database import courses_col
from models.user import has_permission, UserRole
import course_iap
import course_access

router = APIRouter(prefix="/api/courses", tags=["course purchases"])


def purchasable_course(course_id):
    course = courses_col.find_one({"id": course_id}, {"_id": 0})
    if not course or course.get("visibility") == "private":
        raise HTTPException(404, "Course not found")
    if course.get("status") != "active" or course_access.course_ended(course):
        raise HTTPException(400, "This course is not open for purchase")
    return course


@router.get("/{course_id}/purchase-options")
def purchase_options(course_id: str, current_user: dict = Depends(get_current_user)):
    course = purchasable_course(course_id)
    config = course_iap.mapping(course)
    ready = bool(
        (config.get("enabled") or course_iap.allowed_sandbox(current_user["id"]))
        and course_iap.configured()
        and course.get("is_premium")
        and (course.get("premium_price") or 0) > 0
    )
    return {
        "available": ready,
        "entitlement_id": config.get("entitlement_id"),
        "products": {
            "ios": config.get("ios_product_id"),
            "android": config.get("android_product_id"),
        },
    }


@router.post("/{course_id}/confirm-purchase")
def confirm_purchase(
    course_id: str, request: Request, current_user: dict = Depends(get_current_user)
):
    # The request has no receipt/user/product fields; all authority is server-side.
    from rate_limit import rate_limit

    rate_limit(request, "course_purchase_confirmation:" + current_user["id"], 30, 60)
    course = purchasable_course(course_id)
    if not course_iap.mapping(course).get("entitlement_id"):
        raise HTTPException(409, "In-app purchases are not configured for this course")
    return course_iap.reconcile_user(current_user["id"], course_id)[course_id]


@router.put("/{course_id}/purchase-options")
async def set_purchase_options(
    course_id: str, request: Request, current_user: dict = Depends(get_current_user)
):
    # Store products are managed centrally; educators cannot claim another
    # course's product or entitlement to unlock their own course.
    if not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(403, "Only administrators can configure store products")
    if not courses_col.find_one({"id": course_id}):
        raise HTTPException(404, "Course not found")
    data = await request.json()
    config = {
        k: data.get(k)
        for k in ("entitlement_id", "ios_product_id", "android_product_id")
    }
    import re

    if not all(
        isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", v)
        for v in config.values()
    ):
        raise HTTPException(
            400, "Provide an entitlement and both store product identifiers"
        )
    for key, value in config.items():
        fields = (
            ["iap.entitlement_id"]
            if key == "entitlement_id"
            else ["iap.ios_product_id", "iap.android_product_id"]
        )
        if courses_col.find_one(
            {"id": {"$ne": course_id}, "$or": [{field: value} for field in fields]}
        ):
            raise HTTPException(
                409, "This store product or entitlement belongs to another course"
            )
    config["enabled"] = data.get("enabled") is True
    if config["enabled"] and not course_iap.configured():
        raise HTTPException(
            409, "Configure server verification before enabling purchases"
        )
    courses_col.update_one({"id": course_id}, {"$set": {"iap": config}})
    return {"success": True, "iap": config}
