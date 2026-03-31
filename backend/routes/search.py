from fastapi import APIRouter, Depends
from database import courses_col, posts_col, archives_col, cohorts_col, spaces_col
from middleware import get_current_user
from models.user import has_permission, UserRole
import re

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_all(q: str = "", current_user: dict = Depends(get_current_user)):
    if not q or len(q.strip()) < 2:
        return {"courses": [], "community": [], "archives": [], "cohorts": [], "spaces": []}

    pattern = re.compile(re.escape(q.strip()), re.IGNORECASE)

    # Courses
    course_query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
    if not has_permission(current_user["role"], UserRole.FACULTY):
        course_query["status"] = "active"
    courses = list(courses_col.find(course_query, {"_id": 0, "id": 1, "title": 1, "description": 1, "status": 1}).limit(10))

    # Community posts
    posts = list(posts_col.find(
        {"$or": [{"title": pattern}, {"content": pattern}, {"category": pattern}]},
        {"_id": 0, "id": 1, "title": 1, "content": 1, "author_name": 1, "category": 1}
    ).limit(10))
    for p in posts:
        if p.get("content") and len(p["content"]) > 150:
            p["content"] = p["content"][:150] + "..."

    # Archives
    archive_query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
    if not has_permission(current_user["role"], UserRole.FACULTY):
        archive_query["access_level"] = "public"
    archives = list(archives_col.find(archive_query, {"_id": 0, "id": 1, "title": 1, "description": 1, "type": 1}).limit(10))

    # Cohorts
    cohorts = list(cohorts_col.find(
        {"$or": [{"name": pattern}, {"description": pattern}]},
        {"_id": 0, "id": 1, "name": 1, "description": 1}
    ).limit(10))

    # Spaces
    space_results = list(spaces_col.find(
        {"$or": [{"name": pattern}, {"description": pattern}]},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "access_level": 1}
    ).limit(10))

    return {
        "courses": courses,
        "community": posts,
        "archives": archives,
        "cohorts": cohorts,
        "spaces": space_results,
    }
