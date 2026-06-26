from fastapi import APIRouter, HTTPException, Query, Request, Depends
from datetime import datetime, timezone
import uuid
import secrets
from database import courses_col, lessons_col, files_col, enrollments_col, course_invites_col, villages_col, users_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from models.course import CourseStatus
from tier_gating import check_enrollment_limit
from events import emit
# Acyclic: villages.py only imports from database/middleware/models, never routes.
from routes.villages import is_village_member, user_village_ids, _get_village, _can_steward

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("")
async def create_course(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create courses")

    data = await request.json()

    # Village scoping (deep migration Phase 1): a course may be born inside a
    # village. Nullable — platform-wide "commons" content has no village.
    village_id = data.get("village_id")
    if village_id:
        village = _get_village(village_id)
        if not _can_steward(village, current_user):
            raise HTTPException(status_code=403, detail="Only the village's stewards create courses inside it")

    course = {
        "id": str(uuid.uuid4()),
        "title": data["title"],
        "description": data.get("description", ""),
        "image_url": data.get("image_url", ""),
        "instructor_id": current_user["id"],
        "instructor_name": current_user["name"],
        "status": CourseStatus.DRAFT,
        "village_id": village_id,
        # Course-player modules (sections). Embedded list; lessons reference a
        # module by id. Empty = flat course (backward compatible).
        "modules": [],
        # Closed-ecosystem default: new courses are invite-only until the
        # teacher explicitly lists them. (Existing courses without the field
        # are treated as listed for backward compatibility.)
        "visibility": data.get("visibility", "unlisted"),
        "tags": data.get("tags", []),
        "lessons": [],
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if course["visibility"] == "village" and not village_id:
        raise HTTPException(status_code=400, detail="village visibility requires a village_id")
    courses_col.insert_one(course)
    course.pop("_id", None)
    emit("course.created", current_user, "course", course["id"], meta={"title": course["title"]})
    return course


@router.get("")
def list_courses(
    status: str = None,
    village_id: str = None,
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if status:
        query["status"] = status
    if village_id:
        # Scope the catalog to one village. Visibility rules below still apply,
        # so a non-member filtering by a village only sees its listed courses.
        query["village_id"] = village_id

    # Catalog rules (closed ecosystem):
    # - listed = visibility "listed" OR no visibility field (pre-feature courses)
    # - village = visible only to members of course.village_id (third tier)
    # - students/assistants: active + (listed OR their villages' courses)
    # - faculty/elder/ADMIN: the same community view PLUS their own (any state).
    #   Another teacher's draft is their private workspace — it does not appear
    #   in anyone else's catalog, admins included. (Admins can still open a
    #   draft by direct link via get_course, and edit/delete it.)
    visible_or = [{"visibility": "listed"}, {"visibility": {"$exists": False}}]
    my_villages = user_village_ids(current_user["id"])
    if my_villages:
        visible_or.append({"visibility": "village", "village_id": {"$in": my_villages}})
    visible_clause = {"$or": visible_or}
    if has_permission(current_user["role"], UserRole.FACULTY):
        query["$or"] = [
            {"$and": [{"status": CourseStatus.ACTIVE}, visible_clause]},
            {"instructor_id": current_user["id"]},
        ]
    else:
        query["status"] = CourseStatus.ACTIVE
        query.update(visible_clause)

    courses = list(
        courses_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    )
    return courses


@router.get("/{course_id}")
def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Draft privacy: only the instructor or an admin can see a draft.
    # (Unlisted ACTIVE courses are intentionally reachable by direct link/invite.)
    if course.get("status") == CourseStatus.DRAFT:
        if course["instructor_id"] != current_user["id"] and current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=404, detail="Course not found")
    # Village privacy: members-only, even by direct link (404, like drafts,
    # so existence isn't leaked). Instructor and faculty+ pass.
    if course.get("visibility") == "village":
        allowed = (
            course["instructor_id"] == current_user["id"]
            or has_permission(current_user["role"], UserRole.FACULTY)
            or (course.get("village_id") and is_village_member(course["village_id"], current_user["id"]))
        )
        if not allowed:
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
def delete_course(course_id: str, current_user: dict = Depends(get_current_user)):
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
        # Course player: which module (section) this lesson sits in, and an
        # optional full-width hero image. Both nullable — flat lessons still work.
        "module_id": data.get("module_id"),
        "banner_url": (data.get("banner_url") or "").strip(),
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
    for field in ["title", "description", "content", "video_url", "video_file_id", "order", "module_id", "banner_url"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    lessons_col.update_one({"id": lesson_id}, {"$set": update_fields})
    updated = lessons_col.find_one({"id": lesson_id}, {"_id": 0})
    return updated


@router.delete("/{course_id}/lessons/{lesson_id}")
def delete_lesson(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    lessons_col.delete_one({"id": lesson_id, "course_id": course_id})
    courses_col.update_one({"id": course_id}, {"$pull": {"lessons": lesson_id}})
    return {"success": True}


@router.get("/{course_id}/lessons")
def list_lessons(course_id: str, current_user: dict = Depends(get_current_user)):
    lessons = list(lessons_col.find({"course_id": course_id}, {"_id": 0}).sort("order", 1))
    return lessons


# --- Enrollment endpoints ---
@router.post("/{course_id}/enroll")
def enroll_in_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["status"] != CourseStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Course is not open for enrollment")

    existing = enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")

    # Village-only courses: members of the village enroll directly (no invite
    # code needed); everyone else needs to belong to the village first.
    if course.get("visibility") == "village":
        is_staff = course["instructor_id"] == current_user["id"] or has_permission(current_user["role"], UserRole.FACULTY)
        if not is_staff and not (course.get("village_id") and is_village_member(course["village_id"], current_user["id"])):
            raise HTTPException(status_code=403, detail="This course lives inside a village — join the village first")

    # Premium courses require purchase (fulfilled via Stripe webhook) — free
    # enrollment is blocked unless you're the instructor or faculty+.
    if course.get("is_premium") and (course.get("premium_price") or 0) > 0:
        is_staff = course["instructor_id"] == current_user["id"] or has_permission(current_user["role"], UserRole.FACULTY)
        if not is_staff:
            raise HTTPException(
                status_code=402,
                detail=f"premium_required:{course['premium_price']}",
            )

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

    # Send enrollment email (non-blocking; handler is sync, so no event loop here)
    try:
        from routes.email_notifications import send_enrollment_email, send_in_background
        send_in_background(send_enrollment_email(
            current_user.get("email", ""),
            current_user.get("name", "Learner"),
            course["title"],
            course_id,
        ))
    except Exception:
        pass

    emit("course.enrolled", current_user, "course", course_id)
    return enrollment


@router.post("/{course_id}/unenroll")
def unenroll_from_course(course_id: str, current_user: dict = Depends(get_current_user)):
    result = enrollments_col.delete_one({"user_id": current_user["id"], "course_id": course_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    courses_col.update_one({"id": course_id}, {"$inc": {"enrolled_count": -1}})
    emit("course.unenrolled", current_user, "course", course_id)
    return {"success": True}


@router.get("/{course_id}/enrollment")
def get_enrollment_status(course_id: str, current_user: dict = Depends(get_current_user)):
    enrollment = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id}, {"_id": 0}
    )
    return {"enrolled": enrollment is not None, "enrollment": enrollment}


@router.post("/{course_id}/lessons/{lesson_id}/complete")
def complete_lesson(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
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
    emit("lesson.completed", current_user, "lesson", lesson_id,
         meta={"course_id": course_id, "progress": progress})
    if progress >= 100:
        emit("course.completed", current_user, "course", course_id)
    return {"message": "Lesson completed", "progress": progress}


@router.get("/{course_id}/progress")
def get_course_progress(course_id: str, current_user: dict = Depends(get_current_user)):
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
def list_course_enrollments(course_id: str, current_user: dict = Depends(get_current_user)):
    """List all enrollments for a course (faculty+ only)"""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    enrollments = list(enrollments_col.find({"course_id": course_id}, {"_id": 0}))
    result = []
    for enrollment in enrollments:
        student = users_col.find_one({"id": enrollment["user_id"]}, {"_id": 0, "email": 1})
        result.append({
            **enrollment,
            "user_email": student.get("email", "") if student else "",
        })
    return result


# --- Visibility & invites (closed-ecosystem joining) ---

def _require_course_owner(course_id: str, current_user: dict) -> dict:
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the course instructor can do this")
    return course


# --- Modules (course-player sections) ---

@router.post("/{course_id}/modules")
async def add_module(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = _require_course_owner(course_id, current_user)
    data = await request.json()
    title = (data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Module title required")
    modules = course.get("modules", [])
    module = {"id": str(uuid.uuid4()), "title": title[:160], "order": len(modules)}
    courses_col.update_one({"id": course_id}, {"$push": {"modules": module}})
    return module


@router.put("/{course_id}/modules/{module_id}")
async def update_module(course_id: str, module_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    course = _require_course_owner(course_id, current_user)
    data = await request.json()
    modules = course.get("modules", [])
    if not any(m["id"] == module_id for m in modules):
        raise HTTPException(status_code=404, detail="Module not found")
    for m in modules:
        if m["id"] == module_id:
            if "title" in data:
                m["title"] = (data.get("title") or "").strip()[:160] or m["title"]
            if "order" in data:
                m["order"] = data["order"]
    courses_col.update_one({"id": course_id}, {"$set": {"modules": modules}})
    return {"success": True, "modules": modules}


@router.delete("/{course_id}/modules/{module_id}")
def delete_module(course_id: str, module_id: str, current_user: dict = Depends(get_current_user)):
    _require_course_owner(course_id, current_user)
    courses_col.update_one({"id": course_id}, {"$pull": {"modules": {"id": module_id}}})
    # Lessons that lived in this module become ungrouped (module_id cleared).
    lessons_col.update_many({"course_id": course_id, "module_id": module_id}, {"$set": {"module_id": None}})
    return {"success": True}


@router.post("/{course_id}/visibility")
async def set_visibility(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Set course visibility: 'listed' (community catalog), 'unlisted'
    (invite-only), or 'village' (village members only — requires the course
    to be attached to a village)."""
    course = _require_course_owner(course_id, current_user)
    data = await request.json()
    visibility = data.get("visibility")
    if visibility not in ("listed", "unlisted", "village"):
        raise HTTPException(status_code=400, detail="visibility must be 'listed', 'unlisted', or 'village'")
    if visibility == "village" and not course.get("village_id"):
        raise HTTPException(status_code=400, detail="Attach the course to a village before making it village-only")
    courses_col.update_one({"id": course_id}, {"$set": {"visibility": visibility}})
    return {"success": True, "visibility": visibility}


@router.post("/{course_id}/invite-code")
def get_or_create_invite_code(course_id: str, current_user: dict = Depends(get_current_user)):
    """Return the course's invite code, creating it on first call."""
    course = _require_course_owner(course_id, current_user)
    existing = course_invites_col.find_one({"course_id": course_id, "active": True}, {"_id": 0})
    if existing:
        return {"code": existing["code"]}
    code = secrets.token_urlsafe(6)[:8].replace("_", "x").replace("-", "y").upper()
    course_invites_col.insert_one({
        "id": str(uuid.uuid4()),
        "code": code,
        "course_id": course_id,
        "course_title": course["title"],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
        "active": True,
        "uses": 0,
    })
    return {"code": code}


# NOTE: registered on the courses router but addressed by code, not course id.
@router.get("/invites/{code}/resolve")
def resolve_invite(code: str):
    """PUBLIC: resolve an invite code to course info for the join page.
    No session required — shows enough to decide to sign in and join."""
    invite = course_invites_col.find_one({"code": code.upper(), "active": True}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or no longer active")
    course = courses_col.find_one({"id": invite["course_id"]}, {"_id": 0})
    if not course or course.get("status") != CourseStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="This course is not currently open")
    return {
        "code": invite["code"],
        "course_id": course["id"],
        "title": course["title"],
        "description": course.get("description", ""),
        "instructor_name": course.get("instructor_name", ""),
        "image_url": course.get("image_url", ""),
        "is_premium": bool(course.get("is_premium")) and (course.get("premium_price") or 0) > 0,
        "premium_price": course.get("premium_price", 0),
    }


@router.post("/invites/{code}/accept")
def accept_invite(code: str, current_user: dict = Depends(get_current_user)):
    """Join a course via invite. Free → enroll immediately; premium → tell the
    client to start checkout (fulfillment stays webhook-only)."""
    invite = course_invites_col.find_one({"code": code.upper(), "active": True})
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or no longer active")
    course = courses_col.find_one({"id": invite["course_id"]})
    if not course or course.get("status") != CourseStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="This course is not currently open")

    if enrollments_col.find_one({"user_id": current_user["id"], "course_id": course["id"]}):
        return {"enrolled": True, "course_id": course["id"], "message": "Already enrolled"}

    # Invite codes don't pierce village privacy: village-only courses still
    # require village membership (members never needed the code anyway).
    if course.get("visibility") == "village":
        if not (course.get("village_id") and is_village_member(course["village_id"], current_user["id"])):
            raise HTTPException(status_code=403, detail="This course lives inside a village — join the village first")

    if course.get("is_premium") and (course.get("premium_price") or 0) > 0:
        return {
            "enrolled": False,
            "course_id": course["id"],
            "premium_required": True,
            "premium_price": course["premium_price"],
        }

    check_enrollment_limit(current_user)
    enrollment = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "course_id": course["id"],
        "enrolled_at": datetime.now(timezone.utc),
        "completed_lessons": [],
        "progress": 0.0,
        "status": "active",
        "completed_at": None,
        "via_invite": invite["code"],
    }
    enrollments_col.insert_one(enrollment)
    courses_col.update_one({"id": course["id"]}, {"$inc": {"enrolled_count": 1}})
    course_invites_col.update_one({"code": invite["code"]}, {"$inc": {"uses": 1}})
    emit("course.enrolled", current_user, "course", course["id"], meta={"via": "invite"})
    return {"enrolled": True, "course_id": course["id"]}
