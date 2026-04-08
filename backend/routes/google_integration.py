import os
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
import urllib.parse
import requests as http_requests
from database import google_tokens_col, lessons_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/google", tags=["google"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

SCOPES = [
    "https://www.googleapis.com/auth/presentations.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _external_base_url(request: Request) -> str:
    """Build the public-facing base URL honoring proxy headers (Railway)."""
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base_url:
        return public_base_url
    return str(request.base_url).rstrip("/")


@router.get("/auth-url")
async def get_google_auth_url(request: Request, current_user: dict = Depends(get_current_user)):
    """Generate Google OAuth URL for connecting Google account."""
    redirect_uri = _external_base_url(request) + "/api/google/callback"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": current_user["id"],
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/callback")
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback - exchanges code for tokens."""
    if error:
        # Redirect to frontend with error
        return RedirectResponse(url=f"/?google_error={error}")

    if not code:
        return RedirectResponse(url="/?google_error=no_code")

    user_id = state

    redirect_uri = _external_base_url(request) + "/api/google/callback"

    # Exchange code for tokens
    token_response = http_requests.post(
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
        error_detail = token_response.json().get("error_description", "token_exchange_failed")
        return RedirectResponse(url=f"/?google_error={error_detail}")

    tokens = token_response.json()

    # Store tokens
    google_tokens_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in"),
                "scope": tokens.get("scope"),
                "connected_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )

    # Redirect back to frontend settings page with success
    return RedirectResponse(url="/settings?google_connected=true")


@router.get("/status")
async def google_status(current_user: dict = Depends(get_current_user)):
    """Check if user has connected their Google account."""
    token = google_tokens_col.find_one({"user_id": current_user["id"]}, {"_id": 0})
    return {"connected": token is not None}


@router.delete("/disconnect")
async def disconnect_google(current_user: dict = Depends(get_current_user)):
    """Disconnect Google account."""
    google_tokens_col.delete_one({"user_id": current_user["id"]})
    return {"success": True}


def get_valid_access_token(user_id: str) -> str:
    """Get a valid access token, refreshing if needed."""
    token_data = google_tokens_col.find_one({"user_id": user_id})
    if not token_data:
        raise HTTPException(status_code=400, detail="Google account not connected")

    # Try refreshing the token
    if token_data.get("refresh_token"):
        refresh_response = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": token_data["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        if refresh_response.status_code == 200:
            new_tokens = refresh_response.json()
            google_tokens_col.update_one(
                {"user_id": user_id},
                {"$set": {"access_token": new_tokens["access_token"]}},
            )
            return new_tokens["access_token"]

    return token_data["access_token"]


@router.get("/slides")
async def list_google_slides(current_user: dict = Depends(get_current_user)):
    """List user's Google Slides presentations."""
    access_token = get_valid_access_token(current_user["id"])

    response = http_requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "q": "mimeType='application/vnd.google-apps.presentation'",
            "fields": "files(id,name,modifiedTime,thumbnailLink,webViewLink)",
            "orderBy": "modifiedTime desc",
            "pageSize": 50,
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch slides")

    files = response.json().get("files", [])
    return {"slides": files}


@router.get("/docs")
async def list_google_docs(current_user: dict = Depends(get_current_user)):
    """List user's Google Docs documents."""
    access_token = get_valid_access_token(current_user["id"])

    response = http_requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "q": "mimeType='application/vnd.google-apps.document'",
            "fields": "files(id,name,modifiedTime,thumbnailLink,webViewLink)",
            "orderBy": "modifiedTime desc",
            "pageSize": 50,
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch docs")

    files = response.json().get("files", [])
    return {"docs": files}


@router.post("/slides/{slide_id}/import")
async def import_google_slide(slide_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Import a Google Slide presentation as a lesson resource."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can import")

    data = await request.json()
    lesson_id = data.get("lesson_id")
    course_id = data.get("course_id")

    access_token = get_valid_access_token(current_user["id"])

    # Get slide metadata
    response = http_requests.get(
        f"https://slides.googleapis.com/v1/presentations/{slide_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "presentationId,title,slides"},
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch slide")

    slide_data = response.json()
    slide_count = len(slide_data.get("slides", []))

    import_record = {
        "type": "google_slide",
        "google_id": slide_id,
        "title": slide_data.get("title", "Untitled"),
        "slide_count": slide_count,
        "embed_url": f"https://docs.google.com/presentation/d/{slide_id}/embed",
        "view_url": f"https://docs.google.com/presentation/d/{slide_id}/view",
        "imported_by": current_user["id"],
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }

    if lesson_id:
        lessons_col.update_one(
            {"id": lesson_id},
            {"$addToSet": {"google_resources": import_record}},
        )

    return {"success": True, "import": import_record}


@router.post("/docs/{doc_id}/import")
async def import_google_doc(doc_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Import a Google Doc as lesson content."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can import")

    data = await request.json()
    lesson_id = data.get("lesson_id")

    access_token = get_valid_access_token(current_user["id"])

    # Get doc content as plain text
    response = http_requests.get(
        f"https://docs.google.com/document/d/{doc_id}/export",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"mimeType": "text/plain"},
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch doc")

    doc_text = response.text

    # Get doc metadata
    meta_response = http_requests.get(
        f"https://www.googleapis.com/drive/v3/files/{doc_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "id,name,webViewLink"},
    )
    doc_meta = meta_response.json() if meta_response.status_code == 200 else {}

    import_record = {
        "type": "google_doc",
        "google_id": doc_id,
        "title": doc_meta.get("name", "Untitled"),
        "content_preview": doc_text[:500],
        "view_url": doc_meta.get("webViewLink", f"https://docs.google.com/document/d/{doc_id}"),
        "imported_by": current_user["id"],
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }

    if lesson_id:
        lessons_col.update_one(
            {"id": lesson_id},
            {
                "$addToSet": {"google_resources": import_record},
                "$set": {"content": doc_text},
            },
        )

    return {"success": True, "import": import_record, "content": doc_text}
