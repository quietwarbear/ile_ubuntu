from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from database import (
    courses_col, enrollments_col, users_col, cohorts_col,
    posts_col, archives_col, spaces_col, live_sessions_col, lessons_col,
)
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _course_stats_maps():
    """Per-course enrollment stats and lesson counts in two indexed
    aggregations (replaces the per-course find loops that scanned
    enrollments N times — eval brief §11.2.5)."""
    enr_stats = {
        row["_id"]: row
        for row in enrollments_col.aggregate([
            {"$group": {
                "_id": "$course_id",
                "total": {"$sum": 1},
                "avg_progress": {"$avg": {"$ifNull": ["$progress", 0]}},
                "completions": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            }},
        ])
    }
    lesson_counts = {
        row["_id"]: row["n"]
        for row in lessons_col.aggregate([
            {"$group": {"_id": "$course_id", "n": {"$sum": 1}}},
        ])
    }
    return enr_stats, lesson_counts


@router.get("/dashboard")
def get_analytics_dashboard(current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # --- Platform Overview ---
    total_users = users_col.count_documents({})
    users_by_role = {role: 0 for role in ["admin", "elder", "faculty", "assistant", "student"]}
    for row in users_col.aggregate([{"$group": {"_id": "$role", "n": {"$sum": 1}}}]):
        if row["_id"] in users_by_role:
            users_by_role[row["_id"]] = row["n"]

    total_courses = courses_col.count_documents({})
    active_courses = courses_col.count_documents({"status": "active"})
    total_lessons = lessons_col.count_documents({})
    total_cohorts = cohorts_col.count_documents({})
    total_spaces = spaces_col.count_documents({})
    total_archives = archives_col.count_documents({})
    total_posts = posts_col.count_documents({})

    # --- Enrollment Stats ---
    total_enrollments = enrollments_col.count_documents({})
    new_enrollments_week = enrollments_col.count_documents({"enrolled_at": {"$gte": week_ago}})
    new_enrollments_month = enrollments_col.count_documents({"enrolled_at": {"$gte": month_ago}})
    completed_enrollments = enrollments_col.count_documents({"status": "completed"})

    # --- Course Performance ---
    enr_stats, lesson_counts = _course_stats_maps()
    courses = list(courses_col.find({}, {"_id": 0, "id": 1, "title": 1, "enrolled_count": 1, "status": 1}))
    course_stats = []
    for c in courses[:20]:
        s = enr_stats.get(c["id"])
        course_stats.append({
            "id": c["id"],
            "title": c["title"],
            "enrolled_count": c.get("enrolled_count", 0),
            "avg_progress": round(s["avg_progress"], 1) if s else 0,
            "completions": s["completions"] if s else 0,
            "lesson_count": lesson_counts.get(c["id"], 0),
            "status": c.get("status", "draft"),
        })
    course_stats.sort(key=lambda x: x["enrolled_count"], reverse=True)

    # --- Cohort Performance ---
    # One indexed aggregation per cohort (was a find_one per member×course).
    cohorts = list(cohorts_col.find({}, {"_id": 0, "id": 1, "name": 1, "members": 1, "linked_courses": 1}))
    cohort_stats = []
    for ch in cohorts[:10]:
        members = ch.get("members", [])
        linked = ch.get("linked_courses", [])
        avg_cohort_progress = 0
        if members and linked:
            row = next(iter(enrollments_col.aggregate([
                {"$match": {"user_id": {"$in": members}, "course_id": {"$in": linked}}},
                {"$group": {"_id": None, "avg": {"$avg": {"$ifNull": ["$progress", 0]}}}},
            ])), None)
            if row and row["avg"] is not None:
                avg_cohort_progress = round(row["avg"], 1)
        cohort_stats.append({
            "id": ch["id"],
            "name": ch["name"],
            "member_count": len(members),
            "linked_courses": len(linked),
            "avg_progress": avg_cohort_progress,
        })

    # --- Community Activity ---
    # Totals + top contributors in a single pass over posts.
    facet = next(iter(posts_col.aggregate([
        {"$facet": {
            "totals": [{"$group": {
                "_id": None,
                "replies": {"$sum": {"$size": {"$ifNull": ["$replies", []]}}},
                "likes": {"$sum": {"$size": {"$ifNull": ["$likes", []]}}},
            }}],
            "contributors": [
                {"$group": {"_id": {"$ifNull": ["$author_name", "Unknown"]}, "posts": {"$sum": 1}}},
                {"$sort": {"posts": -1, "_id": 1}},
                {"$limit": 5},
            ],
        }},
    ])), {"totals": [], "contributors": []})
    totals = facet["totals"][0] if facet["totals"] else {"replies": 0, "likes": 0}
    top_contributors = [{"name": r["_id"], "posts": r["posts"]} for r in facet["contributors"]]

    # --- Live Sessions ---
    total_sessions = live_sessions_col.count_documents({})
    live_now = live_sessions_col.count_documents({"status": "live"})

    return {
        "overview": {
            "total_users": total_users,
            "users_by_role": users_by_role,
            "total_courses": total_courses,
            "active_courses": active_courses,
            "total_lessons": total_lessons,
            "total_cohorts": total_cohorts,
            "total_spaces": total_spaces,
            "total_archives": total_archives,
            "total_posts": total_posts,
            "total_sessions": total_sessions,
            "live_now": live_now,
        },
        "enrollment": {
            "total": total_enrollments,
            "new_this_week": new_enrollments_week,
            "new_this_month": new_enrollments_month,
            "completed": completed_enrollments,
            "completion_rate": round((completed_enrollments / total_enrollments * 100), 1) if total_enrollments > 0 else 0,
        },
        "courses": course_stats,
        "cohorts": cohort_stats,
        "community": {
            "total_posts": total_posts,
            "total_replies": totals.get("replies", 0),
            "total_likes": totals.get("likes", 0),
            "top_contributors": top_contributors,
        },
    }


@router.get("/enrollment-trends")
def get_enrollment_trends(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Return daily enrollment counts for the last N days."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Single grouped query (was one count_documents per day = N+1 round trips).
    counts = {
        row["_id"]: row["n"]
        for row in enrollments_col.aggregate([
            {"$match": {"enrolled_at": {"$gte": window_start}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$enrolled_at"}},
                "n": {"$sum": 1},
            }},
        ])
    }

    trend_data = []
    for i in range(days, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        trend_data.append({"date": day, "enrollments": counts.get(day, 0)})
    return trend_data


@router.get("/export/csv")
def export_analytics_csv(current_user: dict = Depends(get_current_user)):
    """Export course performance as CSV data."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    from fastapi.responses import StreamingResponse
    import io, csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course Title", "Status", "Enrolled", "Avg Progress", "Completions", "Lessons"])

    enr_stats, lesson_counts = _course_stats_maps()
    courses = list(courses_col.find({}, {"_id": 0, "id": 1, "title": 1, "status": 1}))
    for c in courses:
        s = enr_stats.get(c["id"])
        writer.writerow([
            c["title"],
            c.get("status", "draft"),
            s["total"] if s else 0,
            round(s["avg_progress"], 1) if s else 0,
            s["completions"] if s else 0,
            lesson_counts.get(c["id"], 0),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ile_ubuntu_analytics.csv"},
    )
