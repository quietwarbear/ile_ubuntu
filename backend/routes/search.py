from fastapi import APIRouter, Depends
from database import courses_col, posts_col, archives_col, cohorts_col, spaces_col
from middleware import get_current_user
from models.user import has_permission, UserRole
import re

router = APIRouter(prefix="/api/search", tags=["search"])

# Hybrid search (eval §11.2.4): $text first — indexed, word-based, ranked by
# relevance — then the old case-insensitive regex as a fallback when text
# search returns nothing for a section. The fallback keeps the live search
# bar's partial-word matches working ("phi" still finds "Philosophy") and
# keeps search alive even if a text index is missing.


def _sort_key(sort: str, default_field="created_at"):
    if sort == "popularity":
        return [("enrolled_count", -1)]
    if sort == "date":
        return [("created_at", -1)]
    return [(default_field, 1)]


def _hybrid_find(col, q, regex_or, filters, projection, sort_spec, limit, relevance):
    """$text (ranked when sort=relevance), falling back to regex on zero hits
    or missing index. Both paths apply the same non-search filters."""
    text_query = {"$text": {"$search": q}, **filters}
    try:
        if relevance:
            docs = list(
                col.find(text_query, {**projection, "_score": {"$meta": "textScore"}})
                .sort([("_score", {"$meta": "textScore"})]).limit(limit)
            )
            for d in docs:
                d.pop("_score", None)
        else:
            docs = list(col.find(text_query, projection).sort(sort_spec).limit(limit))
        if docs:
            return docs
    except Exception:
        pass  # no text index (or engine without $text) — regex below
    return list(col.find({**regex_or, **filters}, projection).sort(sort_spec).limit(limit))


def _search_courses(q, pattern, sort, limit, status, is_faculty):
    filters = {}
    if status:
        filters["status"] = status
    elif not is_faculty:
        filters["status"] = "active"
    return _hybrid_find(
        courses_col, q,
        {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]},
        filters,
        {"_id": 0, "id": 1, "title": 1, "description": 1, "status": 1, "enrolled_count": 1, "tags": 1, "created_at": 1},
        _sort_key(sort, "title"), limit, sort == "relevance",
    )


def _search_community(q, pattern, sort, limit):
    posts = _hybrid_find(
        posts_col, q,
        {"$or": [{"title": pattern}, {"content": pattern}, {"category": pattern}]},
        {},
        {"_id": 0, "id": 1, "title": 1, "content": 1, "author_name": 1, "category": 1, "created_at": 1},
        [("created_at", -1)], limit, sort == "relevance",
    )
    for p in posts:
        if p.get("content") and len(p["content"]) > 150:
            p["content"] = p["content"][:150] + "..."
    return posts


def _search_archives(q, pattern, sort, limit, access_level, is_faculty):
    filters = {}
    if access_level:
        filters["access_level"] = access_level
    elif not is_faculty:
        filters["access_level"] = "public"
    return _hybrid_find(
        archives_col, q,
        {"$or": [{"title": pattern}, {"description": pattern}, {"tags": pattern}]},
        filters,
        {"_id": 0, "id": 1, "title": 1, "description": 1, "type": 1, "access_level": 1, "tags": 1, "created_at": 1},
        [("created_at", -1)], limit, sort == "relevance",
    )


def _search_cohorts(q, pattern, sort, limit):
    cohorts = _hybrid_find(
        cohorts_col, q,
        {"$or": [{"name": pattern}, {"description": pattern}]},
        {},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "members": 1, "created_at": 1},
        [("created_at", -1)], limit, sort == "relevance",
    )
    for ch in cohorts:
        ch["member_count"] = len(ch.pop("members", []))
    return cohorts


def _search_spaces(q, pattern, sort, limit, access_level):
    filters = {}
    if access_level:
        filters["access_level"] = access_level
    return _hybrid_find(
        spaces_col, q,
        {"$or": [{"name": pattern}, {"description": pattern}]},
        filters,
        {"_id": 0, "id": 1, "name": 1, "description": 1, "access_level": 1, "created_at": 1},
        [("created_at", -1)], limit, sort == "relevance",
    )


@router.get("")
def search_all(
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

    q = q.strip()
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    is_faculty = has_permission(current_user["role"], UserRole.FACULTY)
    results = {}
    total = 0

    searchers = {
        "courses": lambda: _search_courses(q, pattern, sort, limit, status, is_faculty),
        "community": lambda: _search_community(q, pattern, sort, limit),
        "archives": lambda: _search_archives(q, pattern, sort, limit, access_level, is_faculty),
        "cohorts": lambda: _search_cohorts(q, pattern, sort, limit),
        "spaces": lambda: _search_spaces(q, pattern, sort, limit, access_level),
    }

    for section, searcher in searchers.items():
        if not type or type == section:
            items = searcher()
            results[section] = items
            total += len(items)

    results["total"] = total
    return results
