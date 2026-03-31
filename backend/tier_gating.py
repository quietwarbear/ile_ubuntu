"""
Subscription tier gating middleware.
Faculty/Elder/Admin bypass all tier restrictions (they are creators/managers).
Tier restrictions only apply to students and assistants.
"""

from fastapi import HTTPException
from database import enrollments_col

# Tier hierarchy: explorer < scholar < elder_circle
TIER_HIERARCHY = {
    "explorer": 0,
    "scholar": 1,
    "elder_circle": 2,
}

# Roles that bypass all tier restrictions
BYPASS_ROLES = {"faculty", "elder", "admin"}

ENROLLMENT_LIMITS = {
    "explorer": 2,
    "scholar": 999999,
    "elder_circle": 999999,
}


def get_user_tier(user: dict) -> str:
    return user.get("subscription_tier", "explorer")


def has_tier(user: dict, required_tier: str) -> bool:
    """Check if user's tier meets the required level."""
    if user.get("role") in BYPASS_ROLES:
        return True
    user_tier = get_user_tier(user)
    return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


def check_enrollment_limit(user: dict):
    """Raise 403 if user has hit their enrollment limit."""
    if user.get("role") in BYPASS_ROLES:
        return
    tier = get_user_tier(user)
    limit = ENROLLMENT_LIMITS.get(tier, 2)
    current_count = enrollments_col.count_documents({"user_id": user["id"]})
    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"tier_limit:enrollment:{tier}:{limit}",
        )


def require_tier(user: dict, required_tier: str, feature: str):
    """Raise 403 if user doesn't have the required tier."""
    if not has_tier(user, required_tier):
        raise HTTPException(
            status_code=403,
            detail=f"tier_required:{required_tier}:{feature}",
        )
