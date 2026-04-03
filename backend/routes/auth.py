from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone, timedelta
import os
import uuid
import urllib.parse
import requests
from database import users_col, sessions_col
from middleware import get_current_user
from models.user import UserRole
from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone, timedelta
import os
import uuid
import urllib.parse
import requests
from passlib.context import CryptContext
from database import users_col, sessions_col
from middleware import get_current_user
from models.user import UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_session(user_id: str) -> dict:
    """Create a session for a user and return session info."""
    session_id = str(uuid.uuid4())
    session_token = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    sessions_col.insert_one(session_data)
    return {"session_id": session_id, "session_token": session_token}


@router.post("/register")
async def register(request: Request):
    """Register a new user with email and password."""
    data = await request.json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not name:
        name = email.split("@")[0]

    # Check if user already exists
    existing = users_col.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try signing in instead.")

    user_data = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "picture": "",
        "role": UserRole.STUDENT,
        "bio": "",
        "auth_provider": "password",
        "password_hash": pwd_context.hash(password),
        "created_at": datetime.now(timezone.utc),
    }
    users_col.insert_one(user_data)

    session = _create_session(user_data["id"])
    return {
        "success": True,
        "user_id": user_data["id"],
        **session,
    }


@router.post("/login")
async def login(request: Request):
    """Sign in with email and password."""
    data = await request.json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    user = users_col.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # If user signed up via Google and has no password, tell them
    if not user.get("password_hash"):
        raise HTTPException(
            status_code=401,
            detail="This account uses Google sign-in. Please use the Google button or set a password in Settings."
        )

    if not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session = _create_session(user["id"])
    return {
        "success": True,
        "user_id": user["id"],
        **session,
    }


@router.get("/google/login-url")
async def google_login_url(request: Request, redirect_uri: str = None):
    """Generate Google OAuth URL for user login."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Use the provided redirect_uri (frontend callback) or build from request
    if not redirect_uri:
        redirect_uri = str(request.base_url).rstrip("/") + "/api/auth/google/callback"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


@router.post("/google/callback")
async def google_callback(request: Request):
    """Exchange Google auth code for user session."""
    data = await request.json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    # Exchange code for tokens
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange authorization code")

    tokens = token_response.json()
    access_token = tokens.get("access_token")

    # Get user info from Google
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to get user info")

    google_user = userinfo_response.json()
    email = google_user.get("email")
    name = google_user.get("name", email)
    picture = google_user.get("picture", "")

    # Find or create user
    existing_user = users_col.find_one({"email": email})

    if not existing_user:
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": name,
            "picture": picture,
            "role": UserRole.STUDENT,
            "bio": "",
            "auth_provider": "google",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        user_id = user_data["id"]
    else:
        user_id = existing_user["id"]
        # Update picture/name if changed
        users_col.update_one(
            {"id": user_id},
            {"$set": {"picture": picture, "name": name}},
        )

    session = _create_session(user_id)
    return {
        "success": True,
        "user_id": user_id,
        **session,
    }


@router.post("/profile")
async def create_profile(request: Request):
    """Legacy profile endpoint â kept for backward compatibility."""
    data = await request.json()
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    # Check if this is already a valid session (from Google OAuth flow)
    session = sessions_col.find_one({"session_id": session_id})
    if session:
        return {
            "success": True,
            "user_id": session["user_id"],
            "session_token": session.get("session_token", session_id),
        }

    raise HTTPException(status_code=401, detail="Invalid session")


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

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")


@router.get("/google/login-url")
async def google_login_url(request: Request, redirect_uri: str = None):
    """Generate Google OAuth URL for user login."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Use the provided redirect_uri (frontend callback) or build from request
    if not redirect_uri:
        redirect_uri = str(request.base_url).rstrip("/") + "/api/auth/google/callback"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


@router.post("/google/callback")
async def google_callback(request: Request):
    """Exchange Google auth code for user session."""
    data = await request.json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    # Exchange code for tokens
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange authorization code")

    tokens = token_response.json()
    access_token = tokens.get("access_token")

    # Get user info from Google
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to get user info")

    google_user = userinfo_response.json()
    email = google_user.get("email")
    name = google_user.get("name", email)
    picture = google_user.get("picture", "")

    # Find or create user
    existing_user = users_col.find_one({"email": email})

    if not existing_user:
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": name,
            "picture": picture,
            "role": UserRole.STUDENT,
            "bio": "",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        user_id = user_data["id"]
    else:
        user_id = existing_user["id"]
        # Update picture/name if changed
        users_col.update_one(
            {"id": user_id},
            {"$set": {"picture": picture, "name": name}},
        )

    # Create session
    session_id = str(uuid.uuid4())
    session_token = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    sessions_col.insert_one(session_data)

    return {
        "success": True,
        "user_id": user_id,
        "session_id": session_id,
        "session_token": session_token,
    }


@router.post("/profile")
async def create_profile(request: Request):
    """Legacy profile endpoint — kept for backward compatibility."""
    data = await request.json()
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    # Check if this is already a valid session (from Google OAuth flow)
    session = sessions_col.find_one({"session_id": session_id})
    if session:
        return {
            "success": True,
            "user_id": session["user_id"],
            "session_token": session.get("session_token", session_id),
        }

    raise HTTPException(status_code=401, detail="Invalid session")


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
