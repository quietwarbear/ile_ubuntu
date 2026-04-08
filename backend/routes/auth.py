from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta
import os
import uuid
import urllib.parse
import requests
from pydantic import BaseModel
from passlib.context import CryptContext
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from database import users_col, sessions_col
from middleware import get_current_user
from models.user import UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
DEFAULT_MOBILE_GOOGLE_REDIRECT = os.environ.get(
    "GOOGLE_MOBILE_REDIRECT_URI",
    "ileubuntu://auth/google/callback",
)
ALLOWED_MOBILE_GOOGLE_SCHEMES = {
    scheme.strip()
    for scheme in os.environ.get(
        "GOOGLE_MOBILE_REDIRECT_SCHEMES",
        "ileubuntu,com.ubuntumarket.ileubuntu",
    ).split(",")
    if scheme.strip()
}
ALLOWED_WEB_REDIRECT_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "GOOGLE_WEB_REDIRECT_ORIGINS",
        "https://www.ile-ubuntu.org,https://ile-ubuntu.org",
    ).split(",")
    if origin.strip()
}

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


def _upsert_google_user(google_user: dict) -> str:
    email = (google_user.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google account did not return a usable email.")

    name = google_user.get("name") or email.split("@")[0]
    picture = google_user.get("picture", "")

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
        return user_data["id"]

    user_id = existing_user["id"]
    users_col.update_one(
        {"id": user_id},
        {"$set": {"picture": picture, "name": name}},
    )
    return user_id


def _append_query_value(url: str, key: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append((key, value))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _validate_mobile_redirect_uri(redirect_uri: str) -> str:
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme not in ALLOWED_MOBILE_GOOGLE_SCHEMES:
        raise HTTPException(status_code=400, detail="Unsupported mobile redirect URI.")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Mobile redirect URI must include a host.")
    return redirect_uri


def _validate_redirect_uri(redirect_uri: str) -> str:
    """Validate a redirect URI for both mobile (custom scheme) and web (HTTPS)."""
    parsed = urllib.parse.urlparse(redirect_uri)
    # Allow mobile custom schemes
    if parsed.scheme in ALLOWED_MOBILE_GOOGLE_SCHEMES:
        if not parsed.netloc:
            raise HTTPException(status_code=400, detail="Mobile redirect URI must include a host.")
        return redirect_uri
    # Allow whitelisted web origins
    if parsed.scheme == "https":
        origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        if origin in ALLOWED_WEB_REDIRECT_ORIGINS:
            return redirect_uri
    raise HTTPException(status_code=400, detail="Unsupported redirect URI.")


def _external_base_url(request: Request) -> str:
    """
    Build the public-facing base URL behind a proxy like Railway.

    Railway terminates TLS before forwarding to the app, so `request.base_url`
    can look like `http://...` unless we honor forwarded headers.
    """
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()

    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"

    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base_url:
        return public_base_url

    return str(request.base_url).rstrip("/")


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


class GoogleSessionRequest(BaseModel):
    credential: str


@router.post("/google/session")
async def google_session_login(payload: GoogleSessionRequest):
    """
    Validate a Google OAuth ID token (credential) and log the user in.

    Mirrors the Kindred native Google Sign-In pattern: the client obtains a
    JWT ID token via Google Identity Services / native Google Sign-In, and
    POSTs it here as {"credential": "<jwt>"}. We verify the token server-side
    using the project's GOOGLE_CLIENT_ID, then upsert the user and issue a
    local session. See Google-Auth-Lessons-Kindred.md for the full stack
    checklist and the #1 bug (field-name mismatch on payload).
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID environment variable.")

    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            GoogleRequest(),
            GOOGLE_CLIENT_ID,
        )
        google_user = {
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Unable to validate Google session.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Google session validation failed.") from exc

    user_id = _upsert_google_user(google_user)

    session = _create_session(user_id)
    return {
        "success": True,
        "user_id": user_id,
        **session,
    }


@router.get("/google/login-url")
async def google_login_url(request: Request, redirect_uri: str = "https://www.ile-ubuntu.org/"):
    """
    Return the Google OAuth URL as JSON for the web frontend.

    The web frontend fetches this URL, then redirects the browser to Google.
    After auth, Google redirects back to our /api/auth/google/callback which
    then redirects the user back to the web app with the session_id.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

    app_redirect_uri = _validate_redirect_uri(redirect_uri)
    oauth_callback_uri = _external_base_url(request) + "/api/auth/google/callback"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": oauth_callback_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "online",
        "prompt": "select_account",
        "state": app_redirect_uri,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


@router.get("/google/start")
async def google_login_start(request: Request, redirect_uri: str = DEFAULT_MOBILE_GOOGLE_REDIRECT):
    """
    Start the native-safe Google login flow.

    Google redirects back to our backend HTTPS callback, then the backend
    deep-links into the app using the validated custom-scheme redirect.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

    app_redirect_uri = _validate_mobile_redirect_uri(redirect_uri)
    oauth_callback_uri = _external_base_url(request) + "/api/auth/google/callback"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": oauth_callback_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "online",
        "prompt": "select_account",
        "state": app_redirect_uri,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_login_callback(request: Request, code: str = None, state: str = None, error: str = None):
    app_redirect_uri = _validate_redirect_uri(state or DEFAULT_MOBILE_GOOGLE_REDIRECT)

    if error:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "google_error", error))

    if not code:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "google_error", "no_code"))

    oauth_callback_uri = _external_base_url(request) + "/api/auth/google/callback"

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": oauth_callback_uri,
        },
        timeout=20,
    )

    if token_response.status_code != 200:
        try:
            error_detail = token_response.json().get("error_description", "token_exchange_failed")
        except Exception:
            error_detail = "token_exchange_failed"
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "google_error", error_detail))

    tokens = token_response.json()
    id_token_value = tokens.get("id_token")
    if not id_token_value:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "google_error", "missing_id_token"))

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_value,
            GoogleRequest(),
            GOOGLE_CLIENT_ID,
        )
        user_id = _upsert_google_user(
            {
                "email": idinfo.get("email", ""),
                "name": idinfo.get("name", ""),
                "picture": idinfo.get("picture", ""),
            }
        )
    except Exception:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "google_error", "google_validation_failed"))

    session = _create_session(user_id)
    return RedirectResponse(url=_append_query_value(app_redirect_uri, "session_id", session["session_id"]))


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
