from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import shutil
from pathlib import Path
from database import files_col, lessons_col
from middleware import get_current_user

router = APIRouter(prefix="/api/files", tags=["files"])

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


@router.post("/upload")
async def upload_file(
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
    file_path = UPLOADS_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Enforce video size limit
    if is_video and file_size > MAX_VIDEO_SIZE:
        file_path.unlink()
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
        "file_path": str(file_path),
        "file_size": file_size,
        "mime_type": file.content_type,
        "file_category": file_category,
        "lesson_id": lesson_id,
        "course_id": course_id,
        "uploaded_by": current_user["id"],
        "uploaded_at": datetime.now(timezone.utc),
    }
    files_col.insert_one(file_data)

    if lesson_id:
        lessons_col.update_one(
            {"id": lesson_id},
            {"$addToSet": {"files": file_id}},
        )

    file_data.pop("_id", None)
    return {"success": True, "file": file_data, "download_url": f"/api/files/{file_id}/download"}


@router.get("/{file_id}/download")
async def download_file(file_id: str):
    """Download file - public access for enrolled users via direct link"""
    file_data = files_col.find_one({"id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_data["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_data["original_filename"],
        media_type=file_data["mime_type"],
    )


@router.get("/{file_id}/stream")
async def stream_video(file_id: str):
    """Stream video file with range request support for seeking."""
    from fastapi.responses import StreamingResponse
    from starlette.responses import Response

    file_data = files_col.find_one({"id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    if file_data.get("file_category") != "video":
        raise HTTPException(status_code=400, detail="Not a video file")

    file_path = Path(file_data["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_data["original_filename"],
        media_type=file_data["mime_type"],
    )


@router.get("")
async def list_files(
    lesson_id: Optional[str] = None,
    course_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if lesson_id:
        query["lesson_id"] = lesson_id
    elif course_id:
        query["course_id"] = course_id
    else:
        query["uploaded_by"] = current_user["id"]

    files = list(files_col.find(query, {"_id": 0}).sort("uploaded_at", -1))
    for f in files:
        f["download_url"] = f"/api/files/{f['id']}/download"
    return {"files": files}


@router.delete("/{file_id}")
async def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    file_data = files_col.find_one({"id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    if file_data["uploaded_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

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
