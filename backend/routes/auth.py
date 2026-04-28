from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime, timezone, timedelta
import os
import uuid
import urllib.parse
import requests
import json
import logging

logger = logging.getLogger("auth")
from pydantic import BaseModel
from passlib.context import CryptContext
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from database import (
    users_col,
    sessions_col,
    enrollments_col,
    messages_col,
    notifications_col,
    google_tokens_col,
    payment_transactions_col,
    blog_posts_col,
    blog_comments_col,
    lesson_comments_col,
    quiz_attempts_col,
    spaces_col,
    posts_col,
    live_sessions_col,
)
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
        "ileubuntu,com.ubuntumarket.ileubuntu,capacitor",
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

# Apple Sign In configuration
APPLE_BUNDLE_ID = os.environ.get("APPLE_BUNDLE_ID", "com.ubuntumarket.ileubuntu")
APPLE_SERVICE_ID = os.environ.get("APPLE_SERVICE_ID", "com.ubuntumarket.ileubuntu.signin")
APPLE_MOBILE_REDIRECT_URI = os.environ.get("APPLE_MOBILE_REDIRECT_URI", "ileubuntu://auth/apple/callback")
APPLE_JWKS_CACHE = {}
APPLE_JWKS_CACHE_TIME = 0

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_apple_public_keys():
    """Fetch and cache Apple's public JWKS."""
    global APPLE_JWKS_CACHE, APPLE_JWKS_CACHE_TIME
    now = datetime.now(timezone.utc).timestamp()

    # Cache for 1 hour
    if APPLE_JWKS_CACHE and (now - APPLE_JWKS_CACHE_TIME) < 3600:
        return APPLE_JWKS_CACHE

    try:
        response = requests.get("https://appleid.apple.com/auth/keys", timeout=10)
        response.raise_for_status()
        APPLE_JWKS_CACHE = response.json()
        APPLE_JWKS_CACHE_TIME = now
        return APPLE_JWKS_CACHE
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch Apple public keys.") from exc


def _apple_public_key_from_jwks(kid: str):
    """Extract RSA public key from JWKS by kid."""
    keys = _get_apple_public_keys()
    for key in keys.get("keys", []):
        if key.get("kid") == kid:
            if key.get("kty") != "RSA":
                raise HTTPException(status_code=400, detail="Unsupported key type.")
            try:
                n = int.from_bytes(__import__("base64").urlsafe_b64decode(key["n"] + "=="), "big")
                e = int.from_bytes(__import__("base64").urlsafe_b64decode(key["e"] + "=="), "big")
                public_numbers = RSAPublicNumbers(e, n)
                return public_numbers.public_key(default_backend())
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Failed to construct public key.") from exc
    raise HTTPException(status_code=400, detail="Key ID not found in Apple JWKS.")


def _verify_apple_id_token(token: str):
    """Verify Apple id_token using RS256 with audience and issuer checks."""
    try:
        header = pyjwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=400, detail="Missing 'kid' in token header.")

        # Accept tokens from both the native bundle ID and the web Services ID
        valid_audiences = [APPLE_BUNDLE_ID]
        if APPLE_SERVICE_ID:
            valid_audiences.append(APPLE_SERVICE_ID)

        public_key = _apple_public_key_from_jwks(kid)
        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer="https://appleid.apple.com",
        )
        return payload
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid Apple token.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Apple token verification failed.") from exc


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


def _upsert_apple_user(email: str, name: str = None, picture: str = "") -> str:
    """Upsert a user authenticated via Apple Sign In."""
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Apple account did not return a usable email.")

    if not name:
        name = email.split("@")[0]

    existing_user = users_col.find_one({"email": email})
    if not existing_user:
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": name,
            "picture": picture or "",
            "role": UserRole.STUDENT,
            "bio": "",
            "auth_provider": "apple",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        return user_data["id"]

    user_id = existing_user["id"]
    users_col.update_one(
        {"id": user_id},
        {"$set": {"picture": picture or "", "name": name}},
    )
    return user_id


def _append_query_value(url: str, key: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append((key, value))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _deep_link_redirect(url: str) -> HTMLResponse:
    """
    Return an HTML page that navigates to a custom-scheme deep link.

    SFSafariViewController (iOS) and some desktop browsers do NOT follow
    HTTP 302 redirects to custom URL schemes like ileubuntu://.  Returning
    an HTML page with a JavaScript redirect works reliably across all
    environments.
    """
    escaped = url.replace("&", "&amp;").replace('"', "&quot;")
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Redirecting…</title></head>
<body>
<p>Signing you in…</p>
<script>window.location.href = "{url}";</script>
<noscript><a href="{escaped}">Tap here to continue</a></noscript>
</body>
</html>"""
    return HTMLResponse(content=html)


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

    Flow: frontend fetches this URL → redirects browser to Google →
    Google redirects back to the FRONTEND with ?code= → frontend
    POSTs code to /api/auth/google/callback → backend exchanges code,
    returns session JSON.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

    app_redirect_uri = _validate_redirect_uri(redirect_uri)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": app_redirect_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "online",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/google/callback")
async def google_callback_web(payload: GoogleCallbackRequest):
    """
    Web frontend posts the Google auth code here after the redirect.

    Exchanges the code for tokens, upserts the user, creates a session.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

    _validate_redirect_uri(payload.redirect_uri)

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": payload.code,
            "grant_type": "authorization_code",
            "redirect_uri": payload.redirect_uri,
        },
        timeout=20,
    )

    if token_response.status_code != 200:
        try:
            error_detail = token_response.json().get("error_description", "token_exchange_failed")
        except Exception:
            error_detail = "token_exchange_failed"
        raise HTTPException(status_code=400, detail=error_detail)

    tokens = token_response.json()
    id_token_value = tokens.get("id_token")
    if not id_token_value:
        raise HTTPException(status_code=400, detail="Missing id_token from Google.")

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_value,
            GoogleRequest(),
            GOOGLE_CLIENT_ID,
        )
        user_id = _upsert_google_user({
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Google token validation failed.")

    session = _create_session(user_id)
    return {
        "success": True,
        "user_id": user_id,
        **session,
    }


@router.get("/google/debug")
async def google_debug(request: Request):
    """Temporary diagnostic endpoint — returns the base URL and OAuth config (no secrets)."""
    base = _external_base_url(request)
    return {
        "external_base_url": base,
        "oauth_callback_uri": base + "/api/auth/google/callback",
        "google_client_id_set": bool(GOOGLE_CLIENT_ID),
        "google_client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "google_client_id_prefix": GOOGLE_CLIENT_ID[:20] + "..." if GOOGLE_CLIENT_ID else "",
        "allowed_schemes": list(ALLOWED_MOBILE_GOOGLE_SCHEMES),
        "forwarded_proto": request.headers.get("x-forwarded-proto", ""),
        "forwarded_host": request.headers.get("x-forwarded-host", ""),
        "request_base_url": str(request.base_url),
    }


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

    logger.info("[Google OAuth START] external_base_url=%s", _external_base_url(request))
    logger.info("[Google OAuth START] oauth_callback_uri=%s", oauth_callback_uri)
    logger.info("[Google OAuth START] app_redirect_uri (state)=%s", app_redirect_uri)

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
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/callback")
async def google_login_callback(request: Request, code: str = None, state: str = None, error: str = None):
    logger.info("[Google OAuth CALLBACK] hit! code=%s state=%s error=%s", bool(code), state, error)
    logger.info("[Google OAuth CALLBACK] external_base_url=%s", _external_base_url(request))

    app_redirect_uri = _validate_redirect_uri(state or DEFAULT_MOBILE_GOOGLE_REDIRECT)

    if error:
        print(f"[Google OAuth CALLBACK] Google returned error: {error}")
        return _deep_link_redirect(_append_query_value(app_redirect_uri, "google_error", error))

    if not code:
        print("[Google OAuth CALLBACK] No code received")
        return _deep_link_redirect(_append_query_value(app_redirect_uri, "google_error", "no_code"))

    oauth_callback_uri = _external_base_url(request) + "/api/auth/google/callback"
    print(f"[Google OAuth CALLBACK] token exchange redirect_uri={oauth_callback_uri}")

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
        print(f"[Google OAuth CALLBACK] Token exchange failed: status={token_response.status_code} detail={error_detail}")
        return _deep_link_redirect(_append_query_value(app_redirect_uri, "google_error", error_detail))

    tokens = token_response.json()
    id_token_value = tokens.get("id_token")
    if not id_token_value:
        print("[Google OAuth CALLBACK] No id_token in token response")
        return _deep_link_redirect(_append_query_value(app_redirect_uri, "google_error", "missing_id_token"))

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
    except Exception as exc:
        print(f"[Google OAuth CALLBACK] Token validation failed: {exc}")
        return _deep_link_redirect(_append_query_value(app_redirect_uri, "google_error", "google_validation_failed"))

    session = _create_session(user_id)
    final_url = _append_query_value(app_redirect_uri, "session_id", session["session_id"])
    print(f"[Google OAuth CALLBACK] SUCCESS — deep-linking to {final_url}")
    return _deep_link_redirect(final_url)


class AppleSessionRequest(BaseModel):
    id_token: str


@router.post("/apple/session")
async def apple_session_login(payload: AppleSessionRequest):
    """
    Validate Apple Sign In ID token and log the user in.

    Web popup flow: client obtains an id_token from Apple's JS SDK and POSTs it here.
    We verify the token server-side, upsert the user, and issue a local session.
    """
    try:
        apple_user_info = _verify_apple_id_token(payload.id_token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Apple token verification failed.") from exc

    email = apple_user_info.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Apple account did not return a usable email.")

    # Apple may provide name in the token (for web popup flow)
    name = apple_user_info.get("name") or email.split("@")[0]

    user_id = _upsert_apple_user(email, name)
    session = _create_session(user_id)

    return {
        "success": True,
        "user_id": user_id,
        **session,
    }


@router.get("/apple/start")
async def apple_login_start(request: Request, redirect_uri: str = APPLE_MOBILE_REDIRECT_URI):
    """
    Start the native Apple login flow.

    Redirects to Apple's authorize endpoint. Apple redirects back to our backend
    HTTPS callback, which then deep-links into the app.
    """
    oauth_callback_uri = _external_base_url(request) + "/api/auth/apple/callback"

    # Build Apple OAuth URL — request id_token via form_post so Apple
    # POSTs the token directly to our callback (no code-exchange needed).
    params = {
        "client_id": APPLE_SERVICE_ID,
        "redirect_uri": oauth_callback_uri,
        "response_type": "code id_token",
        "scope": "name email",
        "response_mode": "form_post",
        "state": redirect_uri,
    }
    auth_url = f"https://appleid.apple.com/auth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.post("/apple/callback")
async def apple_login_callback(request: Request):
    """
    Handle Apple's form_post callback after user authorizes.

    Apple sends id_token, code, state, and optionally user info via POST.
    We verify the id_token directly (no code exchange needed) and redirect
    to the app with a session token.
    """
    import json as _json

    form = await request.form()
    id_token_str = form.get("id_token", "")
    state = form.get("state", APPLE_MOBILE_REDIRECT_URI)
    error_val = form.get("error", "")

    # Parse user info (Apple sends JSON string on first auth only)
    user_json = form.get("user", "")
    apple_name = ""
    apple_email = ""
    if user_json:
        try:
            user_data = _json.loads(user_json)
            name_parts = user_data.get("name", {})
            apple_name = f"{name_parts.get('firstName', '')} {name_parts.get('lastName', '')}".strip()
            apple_email = user_data.get("email", "")
        except Exception:
            pass

    # Validate state/redirect_uri
    try:
        app_redirect_uri = _validate_mobile_redirect_uri(state)
    except HTTPException:
        app_redirect_uri = APPLE_MOBILE_REDIRECT_URI

    if error_val:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "apple_error", error_val))

    if not id_token_str:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "apple_error", "no_id_token"))

    try:
        claims = _verify_apple_id_token(id_token_str)
        email = claims.get("email") or apple_email or ""
        name = apple_name or email.split("@")[0]
        user_id = _upsert_apple_user(email, name)
        session = _create_session(user_id)
    except Exception:
        return RedirectResponse(url=_append_query_value(app_redirect_uri, "apple_error", "validation_failed"))

    redirect_url = _append_query_value(app_redirect_uri, "apple_success", "1")
    redirect_url = _append_query_value(redirect_url, "session_id", session["session_id"])
    return RedirectResponse(url=redirect_url)


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


@router.delete("/me")
async def delete_my_account(current_user: dict = Depends(get_current_user)):
    """
    Permanently delete the authenticated user's account and all associated data.

    Required by Apple App Store Guideline 5.1.1(v): apps that allow account
    creation must allow account deletion from within the app.

    This is a hard delete. Each collection is wrapped in its own try/except so
    a single failure does not strand the rest of the cleanup. Returns per-
    collection deletion counts for verifiability.
    """
    user_id = current_user["id"]

    # (collection, filter dict, label)
    deletion_targets = [
        (sessions_col,             {"user_id": user_id},                                              "sessions"),
        (enrollments_col,          {"user_id": user_id},                                              "enrollments"),
        (notifications_col,        {"user_id": user_id},                                              "notifications"),
        (google_tokens_col,        {"user_id": user_id},                                              "google_tokens"),
        (payment_transactions_col, {"user_id": user_id},                                              "payment_transactions"),
        (quiz_attempts_col,        {"user_id": user_id},                                              "quiz_attempts"),
        (blog_posts_col,           {"author_id": user_id},                                            "blog_posts"),
        (blog_comments_col,        {"author_id": user_id},                                            "blog_comments"),
        (lesson_comments_col,      {"author_id": user_id},                                            "lesson_comments"),
        (posts_col,                {"author_id": user_id},                                            "community_posts"),
        (live_sessions_col,        {"host_id": user_id},                                              "live_sessions_hosted"),
        (spaces_col,               {"owner_id": user_id},                                             "spaces_owned"),
        (messages_col,             {"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]},     "messages"),
    ]

    deletion_report = {}
    errors = {}

    for col, query, label in deletion_targets:
        try:
            result = col.delete_many(query)
            deletion_report[label] = result.deleted_count
        except Exception as exc:
            errors[label] = str(exc)
            logger.exception("Account deletion: failed to clear %s for user %s", label, user_id)

    # Remove the user from any spaces they were a member of (but did not own)
    try:
        result = spaces_col.update_many(
            {"members": user_id},
            {"$pull": {"members": user_id}},
        )
        deletion_report["spaces_membership_removed"] = result.modified_count
    except Exception as exc:
        errors["spaces_membership_removed"] = str(exc)
        logger.exception("Account deletion: failed to pull membership for user %s", user_id)

    # Finally, delete the user record itself.
    try:
        result = users_col.delete_one({"id": user_id})
        deletion_report["user_record"] = result.deleted_count
    except Exception as exc:
        errors["user_record"] = str(exc)
        logger.exception("Account deletion: failed to delete user record %s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Account deletion partially failed; please contact support.",
        ) from exc

    if deletion_report.get("user_record", 0) != 1:
        raise HTTPException(status_code=404, detail="User record not found.")

    logger.info("Account deletion complete for user_id=%s report=%s errors=%s",
                user_id, deletion_report, errors)

    response = {"success": True, "deleted": deletion_report}
    if errors:
        response["partial_errors"] = errors
    return response


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
