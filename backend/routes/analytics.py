from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from database import (
    courses_col, enrollments_col, users_col, cohorts_col,
    posts_col, archives_col, spaces_col, live_sessions_col, lessons_col,
)
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_analytics_dashboard(current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # --- Platform Overview ---
    total_users = users_col.count_documents({})
    users_by_role = {}
    for role in ["admin", "elder", "faculty", "assistant", "student"]:
        users_by_role[role] = users_col.count_documents({"role": role})

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
    courses = list(courses_col.find({}, {"_id": 0, "id": 1, "title": 1, "enrolled_count": 1, "status": 1}))
    course_stats = []
    for c in courses[:20]:
        enrs = list(enrollments_col.find({"course_id": c["id"]}, {"_id": 0, "progress": 1, "status": 1}))
        avg_progress = round(sum(e.get("progress", 0) for e in enrs) / len(enrs), 1) if enrs else 0
        completions = sum(1 for e in enrs if e.get("status") == "completed")
        lesson_count = lessons_col.count_documents({"course_id": c["id"]})
        course_stats.append({
            "id": c["id"],
            "title": c["title"],
            "enrolled_count": c.get("enrolled_count", 0),
            "avg_progress": avg_progress,
            "completions": completions,
            "lesson_count": lesson_count,
            "status": c.get("status", "draft"),
        })
    course_stats.sort(key=lambda x: x["enrolled_count"], reverse=True)

    # --- Cohort Performance ---
    cohorts = list(cohorts_col.find({}, {"_id": 0, "id": 1, "name": 1, "members": 1, "linked_courses": 1}))
    cohort_stats = []
    for ch in cohorts[:10]:
        member_count = len(ch.get("members", []))
        linked_count = len(ch.get("linked_courses", []))
        member_progresses = []
        for mid in ch.get("members", []):
            for cid in ch.get("linked_courses", []):
                enr = enrollments_col.find_one({"user_id": mid, "course_id": cid}, {"_id": 0, "progress": 1})
                if enr:
                    member_progresses.append(enr.get("progress", 0))
        avg_cohort_progress = round(sum(member_progresses) / len(member_progresses), 1) if member_progresses else 0
        cohort_stats.append({
            "id": ch["id"],
            "name": ch["name"],
            "member_count": member_count,
            "linked_courses": linked_count,
            "avg_progress": avg_cohort_progress,
        })

    # --- Community Activity ---
    posts = list(posts_col.find({}, {"_id": 0, "author_name": 1, "replies": 1, "likes": 1}))
    total_replies = sum(len(p.get("replies", [])) for p in posts)
    total_likes = sum(len(p.get("likes", [])) for p in posts)

    contributor_map = {}
    for p in posts:
        name = p.get("author_name", "Unknown")
        contributor_map[name] = contributor_map.get(name, 0) + 1
    top_contributors = sorted(contributor_map.items(), key=lambda x: x[1], reverse=True)[:5]
    top_contributors = [{"name": n, "posts": c} for n, c in top_contributors]

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
            "total_replies": total_replies,
            "total_likes": total_likes,
            "top_contributors": top_contributors,
        },
    }


@router.get("/enrollment-trends")
async def get_enrollment_trends(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Return daily enrollment counts for the last N days."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    now = datetime.now(timezone.utc)
    trend_data = []
    for i in range(days, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = enrollments_col.count_documents({
            "enrolled_at": {"$gte": day_start, "$lt": day_end}
        })
        trend_data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "enrollments": count,
        })
    return trend_data


@router.get("/export/csv")
async def export_analytics_csv(current_user: dict = Depends(get_current_user)):
    """Export course performance as CSV data."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        return {"error": "Faculty+ required"}

    from fastapi.responses import StreamingResponse
    import io, csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course Title", "Status", "Enrolled", "Avg Progress", "Completions", "Lessons"])

    courses = list(courses_col.find({}, {"_id": 0, "id": 1, "title": 1, "status": 1}))
    for c in courses:
        enrs = list(enrollments_col.find({"course_id": c["id"]}, {"_id": 0, "progress": 1, "status": 1}))
        avg = round(sum(e.get("progress", 0) for e in enrs) / len(enrs), 1) if enrs else 0
        completions = sum(1 for e in enrs if e.get("status") == "completed")
        lesson_count = lessons_col.count_documents({"course_id": c["id"]})
        writer.writerow([c["title"], c.get("status", "draft"), len(enrs), avg, completions, lesson_count])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ile_ubuntu_analytics.csv"},
    )
