from fastapi import APIRouter, Depends
from database import courses_col, posts_col, archives_col, cohorts_col, spaces_col
from middleware import get_current_user
from models.user import has_permission, UserRole
import re

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_all(
    q: str = "",
    type: str = None,
    status: str = None,
    access_level: str = None,
    sort: str = "relevance",
    limit: int = 15,
    current_user: dict = Depends(get_current_user),
):
    if not q or len(q.strip()) < 2:
        return {"courses": [], "community": [], "archives": [], "cohorts": [], "spaces": [], "total": 0}

    pattern = re.compile(re.escape(q.strip()), re.IGNORECASE)
    is_faculty = has_permission(current_user["role"], UserRole.FACULTY)
    results = {}
    total = 0

    # Courses
    if not type or type == "courses":
        course_query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
        if status:
            course_query["status"] = status
        elif not is_faculty:
            course_query["status"] = "active"
        sort_field = [("enrolled_count", -1)] if sort == "popularity" else [("created_at", -1)] if sort == "date" else [("title", 1)]
        courses = list(courses_col.find(course_query, {"_id": 0, "id": 1, "title": 1, "description": 1, "status": 1, "enrolled_count": 1, "tags": 1, "created_at": 1}).sort(sort_field).limit(limit))
        results["courses"] = courses
        total += len(courses)

    # Community posts
    if not type or type == "community":
        post_query = {"$or": [{"title": pattern}, {"content": pattern}, {"category": pattern}]}
        sort_field = [("created_at", -1)] if sort == "date" else [("created_at", -1)]
        posts = list(posts_col.find(post_query, {"_id": 0, "id": 1, "title": 1, "content": 1, "author_name": 1, "category": 1, "created_at": 1}).sort(sort_field).limit(limit))
        for p in posts:
            if p.get("content") and len(p["content"]) > 150:
                p["content"] = p["content"][:150] + "..."
        results["community"] = posts
        total += len(posts)

    # Archives
    if not type or type == "archives":
        archive_query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
        if access_level:
            archive_query["access_level"] = access_level
        elif not is_faculty:
            archive_query["access_level"] = "public"
        sort_field = [("created_at", -1)]
        archives = list(archives_col.find(archive_query, {"_id": 0, "id": 1, "title": 1, "description": 1, "type": 1, "access_level": 1, "tags": 1, "created_at": 1}).sort(sort_field).limit(limit))
        results["archives"] = archives
        total += len(archives)

    # Cohorts
    if not type or type == "cohorts":
        cohort_query = {"$or": [{"name": pattern}, {"description": pattern}]}
        sort_field = [("created_at", -1)]
        cohorts = list(cohorts_col.find(cohort_query, {"_id": 0, "id": 1, "name": 1, "description": 1, "members": 1, "created_at": 1}).sort(sort_field).limit(limit))
        for ch in cohorts:
            ch["member_count"] = len(ch.pop("members", []))
        results["cohorts"] = cohorts
        total += len(cohorts)

    # Spaces
    if not type or type == "spaces":
        space_query = {"$or": [{"name": pattern}, {"description": pattern}]}
        if access_level:
            space_query["access_level"] = access_level
        sort_field = [("created_at", -1)]
        space_results = list(spaces_col.find(space_query, {"_id": 0, "id": 1, "name": 1, "description": 1, "access_level": 1, "created_at": 1}).sort(sort_field).limit(limit))
        results["spaces"] = space_results
        total += len(space_results)

    results["total"] = total
    return results
