from fastapi import APIRouter, Depends
from database import enrollments_col, courses_col
from middleware import get_current_user

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


@router.get("/my-courses")
async def my_enrolled_courses(current_user: dict = Depends(get_current_user)):
    enrollments = list(
        enrollments_col.find({"user_id": current_user["id"]}, {"_id": 0}).sort("enrolled_at", -1)
    )

    # Enrich with course data
    result = []
    for enrollment in enrollments:
        course = courses_col.find_one({"id": enrollment["course_id"]}, {"_id": 0})
        if course:
            result.append({
                **enrollment,
                "course_title": course.get("title", ""),
                "course_description": course.get("description", ""),
                "instructor_name": course.get("instructor_name", ""),
                "total_lessons": len(course.get("lessons", [])),
                "course_status": course.get("status", ""),
                "course_tags": course.get("tags", []),
            })
    return result
