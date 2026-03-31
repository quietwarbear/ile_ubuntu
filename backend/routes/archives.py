from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import archives_col, courses_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/archives", tags=["archives"])


@router.post("")
async def archive_course(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can archive")

    data = await request.json()
    course_id = data.get("course_id")
    course = courses_col.find_one({"id": course_id}, {"_id": 0})

    archive = {
        "id": str(uuid.uuid4()),
        "title": data.get("title", course["title"] if course else "Untitled"),
        "description": data.get("description", course["description"] if course else ""),
        "type": data.get("type", "course"),
        "source_id": course_id,
        "source_data": course,
        "tags": data.get("tags", []),
        "archived_by": current_user["id"],
        "archived_by_name": current_user["name"],
        "access_level": data.get("access_level", "public"),
        "created_at": datetime.now(timezone.utc),
    }
    archives_col.insert_one(archive)
    archive.pop("_id", None)

    if course_id:
        courses_col.update_one({"id": course_id}, {"$set": {"status": "archived"}})

    return archive


@router.get("")
async def list_archives(type: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if type:
        query["type"] = type
    if not has_permission(current_user["role"], UserRole.FACULTY):
        query["access_level"] = "public"

    archives = list(archives_col.find(query, {"_id": 0}).sort("created_at", -1))
    return archives


@router.get("/{archive_id}")
async def get_archive(archive_id: str, current_user: dict = Depends(get_current_user)):
    archive = archives_col.find_one({"id": archive_id}, {"_id": 0})
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    if archive.get("access_level") == "restricted" and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Access denied")

    return archive


@router.delete("/{archive_id}")
async def delete_archive(archive_id: str, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only admins can delete archives")

    result = archives_col.delete_one({"id": archive_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Archive not found")
    return {"success": True}
