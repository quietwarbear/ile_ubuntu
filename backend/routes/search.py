from fastapi import APIRouter, Depends
from database import courses_col, posts_col, archives_col, cohorts_col, spaces_col
from middleware import get_current_user
from models.user import has_permission, UserRole
import re

router = APIRouter(prefix="/api/search", tags=["search"])


def _sort_key(sort: str, default_field="created_at"):
    if sort == "popularity":
        return [("enrolled_count", -1)]
    if sort == "date":
        return [("created_at", -1)]
    return [(default_field, 1)]


def _search_courses(pattern, sort, limit, status, is_faculty):
    query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
    if status:
        query["status"] = status
    elif not is_faculty:
        query["status"] = "active"
    return list(courses_col.find(
        query, {"_id": 0, "id": 1, "title": 1, "description": 1, "status": 1, "enrolled_count": 1, "tags": 1, "created_at": 1}
    ).sort(_sort_key(sort, "title")).limit(limit))


def _search_community(pattern, sort, limit):
    query = {"$or": [{"title": pattern}, {"content": pattern}, {"category": pattern}]}
    posts = list(posts_col.find(
        query, {"_id": 0, "id": 1, "title": 1, "content": 1, "author_name": 1, "category": 1, "created_at": 1}
    ).sort([("created_at", -1)]).limit(limit))
    for p in posts:
        if p.get("content") and len(p["content"]) > 150:
            p["content"] = p["content"][:150] + "..."
    return posts


def _search_archives(pattern, sort, limit, access_level, is_faculty):
    query = {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]}
    if access_level:
        query["access_level"] = access_level
    elif not is_faculty:
        query["access_level"] = "public"
    return list(archives_col.find(
        query, {"_id": 0, "id": 1, "title": 1, "description": 1, "type": 1, "access_level": 1, "tags": 1, "created_at": 1}
    ).sort([("created_at", -1)]).limit(limit))


def _search_cohorts(pattern, sort, limit):
    query = {"$or": [{"name": pattern}, {"description": pattern}]}
    cohorts = list(cohorts_col.find(
        query, {"_id": 0, "id": 1, "name": 1, "description": 1, "members": 1, "created_at": 1}
    ).sort([("created_at", -1)]).limit(limit))
    for ch in cohorts:
        ch["member_count"] = len(ch.pop("members", []))
    return cohorts


def _search_spaces(pattern, sort, limit, access_level):
    query = {"$or": [{"name": pattern}, {"description": pattern}]}
    if access_level:
        query["access_level"] = access_level
    return list(spaces_col.find(
        query, {"_id": 0, "id": 1, "name": 1, "description": 1, "access_level": 1, "created_at": 1}
    ).sort([("created_at", -1)]).limit(limit))


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

    searchers = {
        "courses": lambda: _search_courses(pattern, sort, limit, status, is_faculty),
        "community": lambda: _search_community(pattern, sort, limit),
        "archives": lambda: _search_archives(pattern, sort, limit, access_level, is_faculty),
        "cohorts": lambda: _search_cohorts(pattern, sort, limit),
        "spaces": lambda: _search_spaces(pattern, sort, limit, access_level),
    }

    for section, searcher in searchers.items():
        if not type or type == section:
            items = searcher()
            results[section] = items
            total += len(items)

    results["total"] = total
    return results
