from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import courses_col, lessons_col, files_col, enrollments_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from models.course import CourseStatus
from tier_gating import check_enrollment_limit
import asyncio

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
        "video_url": data.get("video_url", ""),
        "video_file_id": data.get("video_file_id", ""),
        "order": data.get("order", 0),
        "files": [],
        "has_quiz": False,
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


@router.put("/{course_id}/lessons/{lesson_id}")
async def update_lesson(course_id: str, lesson_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ASSISTANT):
        raise HTTPException(status_code=403, detail="Access denied")

    lesson = lessons_col.find_one({"id": lesson_id, "course_id": course_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    data = await request.json()
    update_fields = {}
    for field in ["title", "description", "content", "video_url", "video_file_id", "order"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    lessons_col.update_one({"id": lesson_id}, {"$set": update_fields})
    updated = lessons_col.find_one({"id": lesson_id}, {"_id": 0})
    return updated


@router.delete("/{course_id}/lessons/{lesson_id}")
async def delete_lesson(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    lessons_col.delete_one({"id": lesson_id, "course_id": course_id})
    courses_col.update_one({"id": course_id}, {"$pull": {"lessons": lesson_id}})
    return {"success": True}


@router.get("/{course_id}/lessons")
async def list_lessons(course_id: str, current_user: dict = Depends(get_current_user)):
    lessons = list(lessons_col.find({"course_id": course_id}, {"_id": 0}).sort("order", 1))
    return lessons


# --- Enrollment endpoints ---
@router.post("/{course_id}/enroll")
async def enroll_in_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["status"] != CourseStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Course is not open for enrollment")

    existing = enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")

    # Tier gating: check enrollment limit
    check_enrollment_limit(current_user)

    enrollment = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "course_id": course_id,
        "enrolled_at": datetime.now(timezone.utc),
        "completed_lessons": [],
        "progress": 0.0,
        "status": "active",
        "completed_at": None,
    }
    enrollments_col.insert_one(enrollment)
    courses_col.update_one({"id": course_id}, {"$inc": {"enrolled_count": 1}})
    enrollment.pop("_id", None)

    # Send enrollment email (non-blocking)
    try:
        from routes.email_notifications import send_enrollment_email
        asyncio.create_task(send_enrollment_email(
            current_user.get("email", ""),
            current_user.get("name", "Learner"),
            course["title"],
            course_id,
        ))
    except Exception:
        pass

    return enrollment


@router.post("/{course_id}/unenroll")
async def unenroll_from_course(course_id: str, current_user: dict = Depends(get_current_user)):
    result = enrollments_col.delete_one({"user_id": current_user["id"], "course_id": course_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    courses_col.update_one({"id": course_id}, {"$inc": {"enrolled_count": -1}})
    return {"success": True}


@router.get("/{course_id}/enrollment")
async def get_enrollment_status(course_id: str, current_user: dict = Depends(get_current_user)):
    enrollment = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id}, {"_id": 0}
    )
    return {"enrolled": enrollment is not None, "enrollment": enrollment}


@router.post("/{course_id}/lessons/{lesson_id}/complete")
async def complete_lesson(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    enrollment = enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id})
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this course")

    lesson = lessons_col.find_one({"id": lesson_id, "course_id": course_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if lesson_id in enrollment.get("completed_lessons", []):
        return {"message": "Already completed", "progress": enrollment["progress"]}

    enrollments_col.update_one(
        {"id": enrollment["id"]},
        {"$addToSet": {"completed_lessons": lesson_id}},
    )

    # Recalculate progress
    total_lessons = lessons_col.count_documents({"course_id": course_id})
    completed_count = len(enrollment.get("completed_lessons", [])) + 1
    progress = round((completed_count / total_lessons) * 100, 1) if total_lessons > 0 else 0

    update = {"progress": progress}
    if progress >= 100:
        update["status"] = "completed"
        update["completed_at"] = datetime.now(timezone.utc)

    enrollments_col.update_one({"id": enrollment["id"]}, {"$set": update})
    return {"message": "Lesson completed", "progress": progress}


@router.get("/{course_id}/progress")
async def get_course_progress(course_id: str, current_user: dict = Depends(get_current_user)):
    enrollment = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id}, {"_id": 0}
    )
    if not enrollment:
        return {"enrolled": False, "progress": 0, "completed_lessons": []}

    total_lessons = lessons_col.count_documents({"course_id": course_id})
    return {
        "enrolled": True,
        "progress": enrollment.get("progress", 0),
        "completed_lessons": enrollment.get("completed_lessons", []),
        "total_lessons": total_lessons,
        "status": enrollment.get("status", "active"),
    }


@router.get("/{course_id}/enrollments")
async def list_course_enrollments(course_id: str, current_user: dict = Depends(get_current_user)):
    """List all enrollments for a course (faculty+ only)"""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    enrollments = list(enrollments_col.find({"course_id": course_id}, {"_id": 0}))
    return enrollments
