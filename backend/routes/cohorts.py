from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import cohorts_col, courses_col, enrollments_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from models.cohort import CohortStatus
from tier_gating import require_tier

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


@router.post("")
async def create_cohort(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create cohorts")

    data = await request.json()
    cohort = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "description": data.get("description", ""),
        "course_ids": data.get("course_ids", []),
        "instructor_id": current_user["id"],
        "instructor_name": current_user["name"],
        "status": CohortStatus.UPCOMING,
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "members": [],
        "max_members": data.get("max_members", 30),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    cohorts_col.insert_one(cohort)
    cohort.pop("_id", None)
    return cohort


@router.get("")
async def list_cohorts(status: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    cohorts = list(cohorts_col.find(query, {"_id": 0}).sort("created_at", -1))
    return cohorts


@router.get("/{cohort_id}")
async def get_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id}, {"_id": 0})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return cohort


@router.put("/{cohort_id}")
async def update_cohort(cohort_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if cohort["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    data = await request.json()
    update_fields = {}
    for field in ["name", "description", "status", "start_date", "end_date", "max_members"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    cohorts_col.update_one({"id": cohort_id}, {"$set": update_fields})
    updated = cohorts_col.find_one({"id": cohort_id}, {"_id": 0})
    return updated


@router.post("/{cohort_id}/join")
async def join_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    # Tier gating: Scholar+ required to join cohorts
    require_tier(current_user, "scholar", "cohort_join")

    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    if current_user["id"] in cohort.get("members", []):
        raise HTTPException(status_code=400, detail="Already a member")

    if len(cohort.get("members", [])) >= cohort.get("max_members", 30):
        raise HTTPException(status_code=400, detail="Cohort is full")

    cohorts_col.update_one(
        {"id": cohort_id},
        {"$addToSet": {"members": current_user["id"]}},
    )

    # Send cohort join email (non-blocking)
    try:
        import asyncio
        from routes.email_notifications import send_cohort_join_email
        asyncio.create_task(send_cohort_join_email(
            current_user.get("email", ""),
            current_user.get("name", "Learner"),
            cohort["name"],
        ))
    except Exception:
        pass

    return {"success": True, "message": "Joined cohort"}


@router.post("/{cohort_id}/leave")
async def leave_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohorts_col.update_one(
        {"id": cohort_id},
        {"$pull": {"members": current_user["id"]}},
    )
    return {"success": True, "message": "Left cohort"}


@router.delete("/{cohort_id}")
async def delete_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if cohort["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    cohorts_col.delete_one({"id": cohort_id})
    return {"success": True}


# --- Course linking ---
@router.post("/{cohort_id}/courses")
async def link_course_to_cohort(cohort_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can link courses")

    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    data = await request.json()
    course_id = data.get("course_id")
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course_id in cohort.get("course_ids", []):
        raise HTTPException(status_code=400, detail="Course already linked")

    cohorts_col.update_one(
        {"id": cohort_id},
        {"$addToSet": {"course_ids": course_id}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return {"success": True}


@router.delete("/{cohort_id}/courses/{course_id}")
async def unlink_course_from_cohort(cohort_id: str, course_id: str, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can unlink courses")

    result = cohorts_col.update_one(
        {"id": cohort_id},
        {"$pull": {"course_ids": course_id}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return {"success": True}


@router.get("/{cohort_id}/detail")
async def get_cohort_detail(cohort_id: str, current_user: dict = Depends(get_current_user)):
    """Get cohort with enriched course and member data."""
    cohort = cohorts_col.find_one({"id": cohort_id}, {"_id": 0})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    # Enrich courses
    linked_courses = []
    for cid in cohort.get("course_ids", []):
        course = courses_col.find_one({"id": cid}, {"_id": 0})
        if course:
            linked_courses.append({
                "id": course["id"],
                "title": course["title"],
                "description": course.get("description", ""),
                "status": course.get("status", "draft"),
                "instructor_name": course.get("instructor_name", ""),
                "lesson_count": len(course.get("lessons", [])),
                "enrolled_count": course.get("enrolled_count", 0),
            })

    # Enrich members with enrollment progress
    from database import users_col
    enriched_members = []
    for uid in cohort.get("members", []):
        u = users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "picture": 1, "role": 1})
        if u:
            member_enrollments = list(enrollments_col.find(
                {"user_id": uid, "course_id": {"$in": cohort.get("course_ids", [])}},
                {"_id": 0, "course_id": 1, "progress": 1, "status": 1},
            ))
            total_progress = 0
            if member_enrollments:
                total_progress = sum(e.get("progress", 0) for e in member_enrollments) / len(cohort.get("course_ids", [1]))
            enriched_members.append({
                **u,
                "enrollments": member_enrollments,
                "overall_progress": round(total_progress, 1),
            })

    return {
        **cohort,
        "linked_courses": linked_courses,
        "enriched_members": enriched_members,
    }
