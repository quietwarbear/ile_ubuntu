"""Cloudflare Stream uploads and captions (items I4 phase 2 and I5).

Playback is not here: viewers get signed URLs from POST /api/files/access-tokens,
after the same access rule as every file. These routes are for course staff:
start an upload, check processing, and manage captions. All of them answer
404 while Stream is not configured (stream.enabled() is False).
"""

from datetime import datetime, timezone
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from database import courses_col, files_col, lessons_col
from middleware import get_current_user
from models.user import UserRole
import file_access
import stream

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["stream"])


@router.get("/config")
def stream_config(current_user: dict = Depends(get_current_user)):
    return {
        "enabled": stream.enabled(),
        "caption_languages": list(stream.CAPTION_LANGUAGES),
        "max_duration_seconds": stream.max_duration(),
    }


def _require_enabled():
    if not stream.enabled():
        raise HTTPException(status_code=404, detail="Video streaming is not configured")


def _staff_on_course(course_id: str, user: dict) -> dict:
    course = courses_col.find_one({"id": course_id}) if course_id else None
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not (user.get("role") == UserRole.ADMIN or file_access._is_staff_on(course, user)):
        raise HTTPException(status_code=403, detail="Only course staff can do that")
    return course


def _stream_file(file_id: str, user: dict) -> dict:
    """A Stream video record the caller may manage: its uploader, an admin,
    or staff on a course it belongs to."""
    _require_enabled()
    record = files_col.find_one({"id": file_id}, {"_id": 0})
    if not record or not record.get("stream_uid"):
        raise HTTPException(status_code=404, detail="Not a streamed video")
    if record.get("uploaded_by") == user["id"] or user.get("role") == UserRole.ADMIN:
        return record
    for course, _lesson in file_access._owning_courses(record):
        if file_access._is_staff_on(course, user):
            return record
    raise HTTPException(status_code=403, detail="Only course staff can do that")


def _upstream(exc: Exception):
    log.warning("stream.error %s", exc)
    raise HTTPException(status_code=502, detail="The video service didn't accept that. Try again shortly.")


@router.post("/uploads")
async def start_upload(request: Request, current_user: dict = Depends(get_current_user)):
    """Body {course_id, lesson_id?, size, filename, mime_type}. Creates the file
    record and returns a one-time upload URL; the browser sends the bytes
    straight to Cloudflare."""
    _require_enabled()
    data = await request.json()
    course_id = data.get("course_id")
    lesson_id = data.get("lesson_id")
    _staff_on_course(course_id, current_user)
    if lesson_id and not lessons_col.find_one({"id": lesson_id, "course_id": course_id}):
        raise HTTPException(status_code=404, detail="Lesson not found")
    size = data.get("size")
    if not isinstance(size, int) or size <= 0:
        raise HTTPException(status_code=400, detail="size (bytes) is required")
    mime = data.get("mime_type") or "video/mp4"
    if not mime.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files go to streaming")
    name = str(data.get("filename") or "lesson video")[:200]

    try:
        upload = stream.create_upload(size, name)
    except stream.StreamError as exc:
        _upstream(exc)

    file_id = str(uuid.uuid4())
    files_col.insert_one({
        "id": file_id,
        "filename": name,
        "original_filename": name,
        "file_size": size,
        "mime_type": mime,
        "file_category": "video",
        "lesson_id": lesson_id,
        "course_id": course_id,
        "uploaded_by": current_user["id"],
        "uploaded_at": datetime.now(timezone.utc),
        "storage": "stream",
        "stream_uid": upload["uid"],
        "stream_state": "uploading",
        "stream_ready": False,
    })
    if lesson_id:
        lessons_col.update_one({"id": lesson_id}, {"$addToSet": {"files": file_id}})
    return {"file_id": file_id, "upload_url": upload["upload_url"]}


def refresh_record(record: dict) -> dict:
    """Pull processing state from Stream; once ready, make sure playback is
    signed-only and ask for automatic captions (once)."""
    details = stream.video(record["stream_uid"])
    update = stream.summarize(details)
    if not update["stream_signed"]:
        stream.require_signed(record["stream_uid"])
        update["stream_signed"] = True
    lang = stream.auto_caption_language()
    if update["stream_ready"] and lang and not record.get("auto_captions_requested"):
        try:
            stream.generate_captions(record["stream_uid"], lang)
            update["auto_captions_requested"] = lang
        except stream.StreamError as exc:
            log.warning("stream.captions.generate %s %s", record["id"], exc)
    files_col.update_one({"id": record["id"]}, {"$set": update})
    return {**record, **update}


@router.post("/{file_id}/refresh")
def refresh(file_id: str, current_user: dict = Depends(get_current_user)):
    record = _stream_file(file_id, current_user)
    try:
        record = refresh_record(record)
    except stream.StreamError as exc:
        _upstream(exc)
    return {key: record.get(key) for key in
            ("stream_state", "stream_ready", "duration_seconds", "stream_error", "auto_captions_requested")}


# --- captions (I5) -----------------------------------------------------------

@router.get("/{file_id}/captions")
def captions(file_id: str, current_user: dict = Depends(get_current_user)):
    record = _stream_file(file_id, current_user)
    try:
        tracks = stream.list_captions(record["stream_uid"])
    except stream.StreamError as exc:
        _upstream(exc)
    return {
        "captions": [{"language": t.get("language"), "label": t.get("label"),
                      "generated": bool(t.get("generated")), "status": t.get("status") or "ready"}
                     for t in tracks],
        "ready": bool(record.get("stream_ready")),
        "languages": list(stream.CAPTION_LANGUAGES),
    }


@router.post("/{file_id}/captions/{lang}/generate")
def generate(file_id: str, lang: str, current_user: dict = Depends(get_current_user)):
    record = _stream_file(file_id, current_user)
    if not record.get("stream_ready"):
        raise HTTPException(status_code=409, detail="The video is still processing")
    try:
        stream.generate_captions(record["stream_uid"], lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except stream.StreamError as exc:
        _upstream(exc)
    return {"success": True}


@router.get("/{file_id}/captions/{lang}/vtt")
def read_vtt(file_id: str, lang: str, current_user: dict = Depends(get_current_user)):
    """{vtt}: the current caption text, for editing."""
    record = _stream_file(file_id, current_user)
    try:
        return {"vtt": stream.get_vtt(record["stream_uid"], lang)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except stream.StreamError as exc:
        _upstream(exc)


@router.put("/{file_id}/captions/{lang}")
async def save_vtt(file_id: str, lang: str, request: Request,
                   current_user: dict = Depends(get_current_user)):
    """Body {vtt: "WEBVTT ..."}: upload a caption file, or save an edited one
    (it replaces the track for that language, including automatic ones)."""
    record = _stream_file(file_id, current_user)
    data = await request.json()
    try:
        stream.put_vtt(record["stream_uid"], lang, data.get("vtt"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except stream.StreamError as exc:
        _upstream(exc)
    return {"success": True}


@router.delete("/{file_id}/captions/{lang}")
def remove_vtt(file_id: str, lang: str, current_user: dict = Depends(get_current_user)):
    record = _stream_file(file_id, current_user)
    try:
        stream.delete_captions(record["stream_uid"], lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except stream.StreamError as exc:
        _upstream(exc)
    return {"success": True}
