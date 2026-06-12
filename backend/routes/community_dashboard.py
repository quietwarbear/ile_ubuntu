"""Community Dashboard v1 — measure what Ubuntu values (eval §6.4).

Five dimensions computed from the activity event stream over the last 30
days, at the collective (cohort-as-village) and individual level. Wellness
is deliberately null until SEL check-ins exist — we don't fake a measure.

Scoring philosophy: raw counts are always returned alongside any score so
educators can see exactly where a number comes from. Scores are absolute
(not relative to peers) — this dashboard never ranks members against each
other. The 'attention' list is an invitation ("these young people may need
you this week"), never a verdict.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from database import cohorts_col, users_col, events_col, mentorship_pairs_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/dashboard", tags=["community-dashboard"])

WINDOW_DAYS = 30
ATTENTION_DAYS = 14

# Event types feeding each dimension (documented so educators can ask "why").
DIMENSIONS = {
    "participation": ["lesson.completed", "live_session.joined", "quiz.attempted", "course.enrolled"],
    "contribution": ["post.created", "post.replied", "lesson.commented"],
    "collaboration": ["post.replied", "live_session.joined", "cohort.joined", "mentorship.note_added"],
    "leadership": ["post.created", "mentorship.goal_completed", "live_session.started", "course.created"],
}

# Per-event weights toward a 0–100 dimension score (capped). Deliberately
# simple and inspectable — not a model, just arithmetic.
WEIGHTS = {
    "lesson.completed": 8, "live_session.joined": 12, "quiz.attempted": 8,
    "course.enrolled": 6, "post.created": 10, "post.replied": 6,
    "lesson.commented": 6, "cohort.joined": 5, "mentorship.note_added": 8,
    "mentorship.goal_completed": 15, "live_session.started": 12, "course.created": 15,
}


def _score(counts: dict, dimension: str) -> int:
    total = sum(WEIGHTS.get(t, 0) * counts.get(t, 0) for t in DIMENSIONS[dimension])
    return min(100, total)


@router.get("/community/{cohort_id}")
def community_dashboard(cohort_id: str, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Faculty access required")

    cohort = cohorts_col.find_one({"id": cohort_id}, {"_id": 0, "id": 1, "name": 1, "members": 1})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    member_ids = cohort.get("members", [])
    if not member_ids:
        return {"cohort": cohort, "dimensions": None, "members": [], "attention": [],
                "message": "No members yet — the dashboard comes alive as the village does."}

    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    attention_cutoff = datetime.now(timezone.utc) - timedelta(days=ATTENTION_DAYS)

    # One pass over the stream: per member, per event type counts + last seen
    # + distinct active days (belonging signal).
    pipeline = [
        {"$match": {"user_id": {"$in": member_ids}, "created_at": {"$gte": since}}},
        {"$group": {
            "_id": {"user": "$user_id", "type": "$type"},
            "count": {"$sum": 1},
            "last": {"$max": "$created_at"},
        }},
    ]
    per_member_counts = {uid: {} for uid in member_ids}
    last_seen = {}
    for row in events_col.aggregate(pipeline):
        uid, etype = row["_id"]["user"], row["_id"]["type"]
        per_member_counts.setdefault(uid, {})[etype] = row["count"]
        if uid not in last_seen or row["last"] > last_seen[uid]:
            last_seen[uid] = row["last"]

    # Active days per member (belonging): distinct event days in the window.
    days_pipeline = [
        {"$match": {"user_id": {"$in": member_ids}, "created_at": {"$gte": since}}},
        {"$group": {"_id": {
            "user": "$user_id",
            "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        }}},
        {"$group": {"_id": "$_id.user", "active_days": {"$sum": 1}}},
    ]
    active_days = {row["_id"]: row["active_days"] for row in events_col.aggregate(days_pipeline)}

    # Mentor roles (leadership signal)
    mentors = {p["mentor_id"] for p in mentorship_pairs_col.find(
        {"mentor_id": {"$in": member_ids}}, {"_id": 0, "mentor_id": 1})}

    members, attention = [], []
    agg = {"participation": 0, "contribution": 0, "collaboration": 0, "leadership": 0, "belonging": 0}
    for uid in member_ids:
        u = users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "picture": 1, "role": 1}) or {"id": uid, "name": "Unknown"}
        counts = per_member_counts.get(uid, {})
        days = active_days.get(uid, 0)

        m = {
            **u,
            "active_days": days,
            "is_mentor": uid in mentors,
            "last_seen": last_seen.get(uid),
            "scores": {
                # Belonging: how regularly they show up (days, not volume).
                "belonging": min(100, days * 8 + (10 if uid in mentors else 0)),
                "participation": _score(counts, "participation"),
                "contribution": _score(counts, "contribution"),
                "collaboration": _score(counts, "collaboration"),
                "leadership": min(100, _score(counts, "leadership") + (25 if uid in mentors else 0)),
            },
            "raw": counts,
        }
        members.append(m)
        for k in agg:
            agg[k] += m["scores"][k]

        seen = last_seen.get(uid)
        if seen is None or seen < attention_cutoff:
            attention.append({**u, "last_seen": seen})

    n = len(members)
    dimensions = {
        k: {"score": round(agg[k] / n)} for k in agg
    }
    # Honest placeholder: no data source yet, so no number.
    dimensions["wellness"] = {"score": None, "note": "Arrives with SEL check-ins — we don't invent a number."}

    members.sort(key=lambda m: (m["name"] or "").lower())

    return {
        "cohort": {"id": cohort["id"], "name": cohort["name"], "member_count": n},
        "window_days": WINDOW_DAYS,
        "dimensions": dimensions,
        "members": members,
        "attention": attention,
    }
