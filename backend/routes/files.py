from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Header, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse, JSONResponse
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import shutil
from html import escape as html_escape
from pathlib import Path
from database import files_col, lessons_col, courses_col, users_col
from middleware import get_current_user
from models.user import has_permission, UserRole
import file_access
import storage
import stream

router = APIRouter(prefix="/api/files", tags=["files"])

# Local disk is only a dev / legacy fallback. In production, files live in object storage
# (see storage.py) because Railway's container disk is ephemeral. Existing records created
# before the S3 migration still carry a "file_path" and are served from disk via the same
# fallback, so old lessons keep working.
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "text/plain": ".txt",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    # Video types
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
    # Audio types (for voice lessons)
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
}

VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB


def _on_ephemeral_host() -> bool:
    """Railway container disk is wiped on every redeploy, so the local-disk
    fallback silently loses files there. Detected via Railway's built-in envs."""
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


MISSING_FILE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>File unavailable</title>
<style>
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#050814; color:#94A3B8; font-family:-apple-system,'Segoe UI',Roboto,sans-serif; }}
  .card {{ max-width:420px; padding:32px; text-align:center; }}
  h1 {{ color:#D4AF37; font-size:16px; letter-spacing:.12em; text-transform:uppercase; margin:0 0 12px; }}
  p {{ font-size:14px; line-height:1.6; margin:0; }}
</style></head>
<body><div class="card">
  <h1>File unavailable</h1>
  <p>{name} is no longer stored on the server. Please ask the instructor to re-upload it to this lesson.</p>
</div></body></html>"""


def _renders_inline(file_data: dict) -> bool:
    """PDFs, images, video and audio render in-browser; documents download."""
    return (
        file_data.get("file_category") in {"image", "video", "audio"}
        or file_data.get("mime_type") == "application/pdf"
    )


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    lesson_id: Optional[str] = Form(None),
    course_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")

    is_video = file.content_type in VIDEO_TYPES

    file_id = str(uuid.uuid4())
    extension = ALLOWED_TYPES[file.content_type]
    filename = f"{file_id}{extension}"

    # Size up-front (without reading into memory) so we can enforce the video cap.
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if is_video and file_size > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=400, detail="Video file too large (max 500MB)")

    # Categorize file type
    if is_video:
        file_category = "video"
    elif file.content_type.startswith("image/"):
        file_category = "image"
    elif file.content_type.startswith("audio/"):
        file_category = "audio"
    else:
        file_category = "document"

    file_data = {
        "id": file_id,
        "filename": filename,
        "original_filename": file.filename,
        "file_size": file_size,
        "mime_type": file.content_type,
        "file_category": file_category,
        "lesson_id": lesson_id,
        "course_id": course_id,
        "uploaded_by": current_user["id"],
        "uploaded_at": datetime.now(timezone.utc),
    }

    if storage.s3_enabled():
        key = storage.build_key(filename)
        try:
            storage.upload_fileobj(file.file, key, file.content_type)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Upload failed: {exc}")
        file_data["storage"] = "s3"
        file_data["s3_key"] = key
    else:
        if _on_ephemeral_host():
            # Refuse rather than accept a file that the next redeploy will destroy.
            raise HTTPException(
                status_code=503,
                detail="File storage is not configured on the server (S3_BUCKET and "
                       "credentials missing). Uploads are disabled until it is, because "
                       "files written to this host's disk are lost on every redeploy.",
            )
        # Local fallback (dev only; not durable on Railway)
        file_path = UPLOADS_DIR / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_data["storage"] = "local"
        file_data["file_path"] = str(file_path)

    files_col.insert_one(file_data)

    if lesson_id:
        lessons_col.update_one(
            {"id": lesson_id},
            {"$addToSet": {"files": file_id}},
        )

    file_data.pop("_id", None)
    return {
        "success": True,
        "file": file_data,
        # Stable path stored in lesson content (the viewer tokenizes it when it
        # renders); the signed URL is for immediate use by the uploader.
        "download_url": f"/api/files/{file_id}/download",
        "signed_url": file_access.signed_path(file_id, current_user["id"]),
    }


def _serve(file_data: dict, inline: Optional[bool] = None):
    """Serve a stored file from S3 (presigned redirect) or local disk (fallback).
    A Cloudflare Stream video redirects to a freshly signed HLS manifest."""
    if file_data.get("stream_uid"):
        if not stream.enabled():
            raise HTTPException(status_code=503, detail="Video streaming is not configured")
        if not file_data.get("stream_ready"):
            raise HTTPException(status_code=409, detail="This video is still processing")
        urls = stream.playback(file_data["stream_uid"], file_data.get("duration_seconds"))
        return RedirectResponse(urls["hls_url"], status_code=307)
    is_video = file_data.get("file_category") == "video"
    if inline is None or is_video:
        # Video is never offered as an attachment: it plays, it doesn't download.
        inline = True if is_video else _renders_inline(file_data)
    original = file_data.get("original_filename") or file_data.get("filename") or "file"
    mime = file_data.get("mime_type") or "application/octet-stream"

    if file_data.get("s3_key"):
        ttl = storage.VIDEO_PRESIGN_TTL if is_video else None
        url = storage.presigned_get(file_data["s3_key"], original, mime, inline=inline, ttl=ttl)
        return RedirectResponse(url, status_code=307)

    file_path = Path(file_data.get("file_path", ""))
    if not file_path.exists():
        # Inline requests come from <iframe>/<img>/<video> tags, where a JSON body
        # renders as raw text inside the lesson page — return a styled page instead.
        if inline:
            name = html_escape(original) if original != "file" else "This file"
            return HTMLResponse(MISSING_FILE_HTML.format(name=name), status_code=404)
        raise HTTPException(
            status_code=404,
            detail="This file is no longer stored on the server (it was saved to local "
                   "disk before durable storage was enabled). Re-upload it to restore it.",
        )
    return FileResponse(
        path=file_path,
        filename=original,
        media_type=mime,
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-store"},
    )


def _requester(x_session_id: Optional[str]) -> Optional[dict]:
    """The signed-in user behind the X-Session-ID header, or None."""
    if not x_session_id:
        return None
    try:
        return get_current_user(x_session_id)
    except HTTPException:
        return None


def _authorize(file_id: str, token: Optional[str], x_session_id: Optional[str]) -> dict:
    """Load the file and enforce file_access.can_access. A playback token
    (``?t=``) stands in for the session header on <video>/<iframe>/<img>; it
    must be valid, for this file, and — when a session is also presented —
    issued to that same user. Access is re-checked for the token's user on
    every request."""
    file_data = files_col.find_one({"id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    if file_access.is_public(file_data):
        return file_data

    user = _requester(x_session_id)
    if token:
        token_user_id = file_access.verify_token(token, file_id)
        if not token_user_id:
            raise HTTPException(status_code=403, detail="Link expired or invalid")
        if user and user["id"] != token_user_id:
            raise HTTPException(status_code=403, detail="Link was issued to someone else")
        if not user:
            user = users_col.find_one({"id": token_user_id}, {"_id": 0})
            if not user:
                raise HTTPException(status_code=403, detail="Link expired or invalid")
    elif not user:
        raise HTTPException(status_code=401, detail="Sign in to view this file")

    if not file_access.can_access(file_data, user):
        ended = file_access.access_ended_for(file_data, user)
        if ended is not None:
            raise AccessEnded(ended)
        raise HTTPException(status_code=403, detail="You don't have access to this file")
    return file_data


class AccessEnded(Exception):
    """I6: the person's access to this file's course is over."""
    def __init__(self, ended):
        self.ended = ended


_ENDED_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Access has ended</title>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#050814;color:#F8FAFC;font-family:Arial,sans-serif;padding:16px}}
main{{max-width:420px;text-align:center}}p{{color:#94A3B8;line-height:1.6}}a{{color:#D4AF37}}</style></head>
<body><main><h1>Your access has ended</h1>
<p>Access to this course's materials ended on {date}. If you think that's a mistake, contact the course organizer.</p>
<p><a href="{site}/">Back to The Ile Ubuntu</a></p></main></body></html>"""


def _ended_response(request: Request, exc: AccessEnded):
    """A clear page for a person who opened the link in a browser tab, the
    usual JSON code (access_ended:<date>) for the app."""
    import course_access
    from routes.email_notifications import PUBLIC_SITE_URL
    if "text/html" in (request.headers.get("accept") or ""):
        date = exc.ended.strftime("%B %-d, %Y") if exc.ended.year > 1 else "an earlier date"
        return HTMLResponse(_ENDED_PAGE.format(date=date, site=PUBLIC_SITE_URL), status_code=403)
    return JSONResponse({"detail": course_access.detail(exc.ended)}, status_code=403)


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    request: Request,
    t: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
):
    """View or download a file. Requires the session header or a playback
    token from POST /api/files/access-tokens; see file_access.py for the rule."""
    try:
        return _serve(_authorize(file_id, t, x_session_id))
    except AccessEnded as exc:
        return _ended_response(request, exc)


@router.get("/{file_id}/stream")
def stream_video(
    file_id: str,
    request: Request,
    t: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
):
    """Stream a video inline. S3 presigned URLs support range requests (seeking)."""
    try:
        file_data = _authorize(file_id, t, x_session_id)
    except AccessEnded as exc:
        return _ended_response(request, exc)
    if file_data.get("file_category") != "video":
        raise HTTPException(status_code=400, detail="Not a video file")
    return _serve(file_data, inline=True)


MAX_TOKEN_BATCH = 100
STREAM_RECHECK_SECONDS = 30


def _stream_playback(record: dict) -> dict:
    """I4 phase 2: signed Cloudflare Stream URLs for someone file_access has
    already let in. While the video is processing, check Stream at most every
    STREAM_RECHECK_SECONDS so the player starts once it's ready (no webhook)."""
    if not stream.enabled():
        return {"state": "unavailable"}
    if not record.get("stream_ready"):
        checked = record.get("stream_checked_at")
        now = datetime.now(timezone.utc)
        if checked and checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        if not checked or (now - checked).total_seconds() >= STREAM_RECHECK_SECONDS:
            files_col.update_one({"id": record["id"]}, {"$set": {"stream_checked_at": now}})
            try:
                from routes.stream_video import refresh_record
                record = refresh_record(record)
            except stream.StreamError as exc:
                import logging
                logging.getLogger(__name__).warning("stream.refresh %s %s", record["id"], exc)
    if not record.get("stream_ready"):
        return {"state": record.get("stream_state") or "processing"}
    return {"state": "ready", **stream.playback(record["stream_uid"], record.get("duration_seconds"))}


@router.post("/access-tokens")
async def issue_access_tokens(request: Request, current_user: dict = Depends(get_current_user)):
    """Short-lived playback tokens for the files this user may read. Body:
    {"file_ids": [...]}. Files the user can't read are simply absent from the
    result, so a page can ask for everything it renders without probing."""
    data = await request.json()
    ids = data.get("file_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise HTTPException(status_code=400, detail="file_ids must be a list of ids")
    ids = list(dict.fromkeys(ids))[:MAX_TOKEN_BATCH]
    out = {}
    ended = {}
    for record in files_col.find({"id": {"$in": ids}}, {"_id": 0}):
        if not file_access.can_access(record, current_user):
            end = file_access.access_ended_for(record, current_user)
            if end is not None:
                import course_access
                ended[record["id"]] = course_access.detail(end)   # I6: say why
            continue
        issued = file_access.issue_token(current_user["id"], record["id"])
        kind = "stream" if record.get("file_category") == "video" else "download"
        out[record["id"]] = {
            **issued,
            "url": f"/api/files/{record['id']}/{kind}?t={issued['token']}",
            "download_url": f"/api/files/{record['id']}/download?t={issued['token']}",
        }
        if record.get("stream_uid"):
            out[record["id"]]["stream"] = _stream_playback(record)
    return {"tokens": out, "ended": ended, "ttl_seconds": file_access.TOKEN_TTL}


@router.get("/integrity/report")
def file_integrity_report(current_user: dict = Depends(get_current_user)):
    """Faculty+: every file record still on the local-disk fallback (i.e. not in S3),
    with whether its bytes actually exist. In production these are lost files that
    need re-uploading; the report tells you exactly which lessons to fix."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Faculty+ required")

    local_records = list(files_col.find(
        {"s3_key": {"$exists": False}, "stream_uid": {"$exists": False}}, {"_id": 0}))
    report = []
    for f in local_records:
        path = Path(f.get("file_path", ""))
        entry = {
            "id": f.get("id"),
            "original_filename": f.get("original_filename"),
            "file_size": f.get("file_size"),
            "uploaded_at": f.get("uploaded_at"),
            "uploaded_by": f.get("uploaded_by"),
            "lesson_id": f.get("lesson_id"),
            "course_id": f.get("course_id"),
            "exists_on_disk": bool(f.get("file_path")) and path.exists(),
        }
        if f.get("lesson_id"):
            lesson = lessons_col.find_one({"id": f["lesson_id"]}, {"_id": 0, "title": 1, "course_id": 1})
            if lesson:
                entry["lesson_title"] = lesson.get("title")
                entry["course_id"] = entry["course_id"] or lesson.get("course_id")
        if entry.get("course_id"):
            course = courses_col.find_one({"id": entry["course_id"]}, {"_id": 0, "title": 1})
            if course:
                entry["course_title"] = course.get("title")
        report.append(entry)

    missing = [r for r in report if not r["exists_on_disk"]]
    return {
        "s3_enabled": storage.s3_enabled(),
        "local_records": len(report),
        "missing_files": len(missing),
        "files": report,
    }


@router.get("")
def list_files(
    lesson_id: Optional[str] = None,
    course_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if lesson_id:
        query["lesson_id"] = lesson_id
        # Student submissions are not course material; they are listed only
        # through routes/submissions.py, never here.
        query["submission_id"] = {"$exists": False}
    elif course_id:
        query["course_id"] = course_id
        query["submission_id"] = {"$exists": False}
    else:
        query["uploaded_by"] = current_user["id"]

    files = [
        f for f in files_col.find(query, {"_id": 0}).sort("uploaded_at", -1)
        if file_access.can_access(f, current_user)
    ]
    for f in files:
        # Tokenized for this caller, so the URL works in a plain <a>/<iframe>.
        # It expires in minutes; pages that stay open refresh it through
        # POST /access-tokens.
        f["download_url"] = file_access.signed_path(f["id"], current_user["id"])
    return {"files": files}


@router.delete("/{file_id}")
def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    file_data = files_col.find_one({"id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    if file_data["uploaded_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if file_data.get("stream_uid") and stream.enabled():
        try:
            stream.delete_video(file_data["stream_uid"])
        except stream.StreamError as exc:
            raise HTTPException(status_code=502, detail=f"Couldn't remove the streamed video: {exc}")
    if file_data.get("s3_key"):
        storage.delete_object(file_data["s3_key"])
    elif file_data.get("file_path"):
        file_path = Path(file_data["file_path"])
        if file_path.exists():
            file_path.unlink()

    files_col.delete_one({"id": file_id})

    if file_data.get("lesson_id"):
        lessons_col.update_one(
            {"id": file_data["lesson_id"]},
            {"$pull": {"files": file_id}},
        )

    return {"success": True}
