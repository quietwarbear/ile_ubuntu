from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone, timedelta
import uuid
import requests
from database import users_col, sessions_col
from middleware import get_current_user
from models.user import UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/profile")
async def create_profile(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    headers = {"X-Session-ID": session_id}
    response = requests.get(
        "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
        headers=headers,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")

    auth_data = response.json()
    existing_user = users_col.find_one({"email": auth_data["email"]})

    if not existing_user:
        user_data = {
            "id": str(uuid.uuid4()),
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data["picture"],
            "role": UserRole.STUDENT,
            "bio": "",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        user_id = user_data["id"]
    else:
        user_id = existing_user["id"]

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": auth_data["session_token"],
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    sessions_col.update_one(
        {"session_id": session_id}, {"$set": session_data}, upsert=True
    )

    return {
        "success": True,
        "user_id": user_id,
        "session_token": auth_data["session_token"],
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user["picture"],
        "role": current_user["role"],
        "bio": current_user.get("bio", ""),
        "subscription_tier": current_user.get("subscription_tier", "explorer"),
        "onboarding_complete": current_user.get("onboarding_complete", False),
        "language": current_user.get("language", "en"),
        "interests": current_user.get("interests", []),
    }


@router.put("/me/onboarding")
async def complete_onboarding(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    update = {"onboarding_complete": True}
    if "interests" in data:
        update["interests"] = data["interests"]
    if "language" in data:
        update["language"] = data["language"]
    users_col.update_one({"id": current_user["id"]}, {"$set": update})
    return {"success": True}


@router.put("/me/language")
async def set_language(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    lang = data.get("language", "en")
    if lang not in ("en", "es", "yo"):
        raise HTTPException(status_code=400, detail="Supported: en, es, yo")
    users_col.update_one({"id": current_user["id"]}, {"$set": {"language": lang}})
    return {"success": True, "language": lang}


@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    from models.user import has_permission, UserRole
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    users = list(users_col.find({}, {"_id": 0}))
    return users


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    from models.user import has_permission, UserRole
    if not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only admins/elders can change roles")

    data = await request.json()
    new_role = data.get("role")
    if new_role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")

    result = users_col.update_one({"id": user_id}, {"$set": {"role": new_role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True, "message": f"Role updated to {new_role}"}
