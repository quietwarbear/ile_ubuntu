from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import courses_col, lessons_col, files_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from models.course import CourseStatus

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("")
async def create_course(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create courses")

    data = await request.json()
    course = {
        "id": str(uuid.uuid4()),
        "title": data["title"],
        "description": data.get("description", ""),
        "image_url": data.get("image_url", ""),
        "instructor_id": current_user["id"],
        "instructor_name": current_user["name"],
        "status": CourseStatus.DRAFT,
        "tags": data.get("tags", []),
        "lessons": [],
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    courses_col.insert_one(course)
    course.pop("_id", None)
    return course


@router.get("")
async def list_courses(status: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    # Faculty+ see all; students see only active
    if not has_permission(current_user["role"], UserRole.FACULTY):
        query["status"] = CourseStatus.ACTIVE

    courses = list(courses_col.find(query, {"_id": 0}).sort("created_at", -1))
    return courses


@router.get("/{course_id}")
async def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}")
async def update_course(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    data = await request.json()
    update_fields = {}
    for field in ["title", "description", "image_url", "status", "tags"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    courses_col.update_one({"id": course_id}, {"$set": update_fields})
    updated = courses_col.find_one({"id": course_id}, {"_id": 0})
    return updated


@router.delete("/{course_id}")
async def delete_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    lessons_col.delete_many({"course_id": course_id})
    courses_col.delete_one({"id": course_id})
    return {"success": True}


# --- Lesson sub-routes ---
@router.post("/{course_id}/lessons")
async def create_lesson(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ASSISTANT):
        raise HTTPException(status_code=403, detail="Access denied")

    data = await request.json()
    lesson = {
        "id": str(uuid.uuid4()),
        "course_id": course_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "content": data.get("content", ""),
        "order": data.get("order", 0),
        "files": [],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    lessons_col.insert_one(lesson)
    lesson.pop("_id", None)

    courses_col.update_one(
        {"id": course_id},
        {"$addToSet": {"lessons": lesson["id"]}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return lesson


@router.get("/{course_id}/lessons")
async def list_lessons(course_id: str, current_user: dict = Depends(get_current_user)):
    lessons = list(lessons_col.find({"course_id": course_id}, {"_id": 0}).sort("order", 1))
    return lessons
