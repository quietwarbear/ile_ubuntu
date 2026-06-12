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

from database import cohorts_col, users_col, events_col, mentorship_pairs_col, checkins_col, villages_col
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


def _compute_dashboard(member_ids: list) -> dict:
    """The five Ubuntu dimensions for any set of members — shared by the
    cohort view and the village view (Phase 3: measures go village-wide)."""
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

    # Wellness: average of check-in scores (1–5 → 0–100) over the window.
    # Notes are NEVER read here — scores only.
    since_day = since.strftime("%Y-%m-%d")
    wellness_pipeline = [
        {"$match": {"user_id": {"$in": member_ids}, "day": {"$gte": since_day}}},
        {"$group": {
            "_id": "$user_id",
            "avg": {"$avg": {"$divide": [{"$add": ["$mood", "$connected", "$confident"]}, 3]}},
            "checkins": {"$sum": 1},
        }},
    ]
    wellness_by_member = {
        row["_id"]: {"score": round(row["avg"] * 20), "checkins": row["checkins"]}
        for row in checkins_col.aggregate(wellness_pipeline)
    }

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
                "wellness": wellness_by_member.get(uid, {}).get("score"),
            },
            "raw": counts,
        }
        members.append(m)
        for k in agg:
            agg[k] += m["scores"][k]

        seen = last_seen.get(uid)
        # PyMongo (tz_aware=False, our default client) returns NAIVE UTC
        # datetimes; attention_cutoff is aware. Normalize before comparing —
        # without this the whole dashboard 500s for any scope with activity.
        if seen is not None and seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        if seen is None or seen < attention_cutoff:
            attention.append({**u, "last_seen": seen})

    n = len(members)
    dimensions = {
        k: {"score": round(agg[k] / n)} for k in agg
    }
    # Wellness: collective average across members who checked in; honest null otherwise.
    with_wellness = [m["scores"]["wellness"] for m in members if m["scores"]["wellness"] is not None]
    if with_wellness:
        dimensions["wellness"] = {
            "score": round(sum(with_wellness) / len(with_wellness)),
            "note": f"From {len(with_wellness)} of {n} members checking in — words stay private, always.",
        }
    else:
        dimensions["wellness"] = {"score": None, "note": "Comes alive as members check in — no one's words are ever shown."}

    members.sort(key=lambda m: (m["name"] or "").lower())

    return {
        "window_days": WINDOW_DAYS,
        "dimensions": dimensions,
        "members": members,
        "attention": attention,
    }


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

    result = _compute_dashboard(member_ids)
    return {
        "cohort": {"id": cohort["id"], "name": cohort["name"], "member_count": len(member_ids)},
        **result,
    }


@router.get("/village/{village_id}")
def village_dashboard(village_id: str, current_user: dict = Depends(get_current_user)):
    """The same five dimensions, scoped to the whole village (Phase 3).
    Faculty+ or the village's own stewards (educators/elders) may look.
    Adds: the village's mentors (for 'suggest a mentor check-in' routing —
    precursor to eval §7.5 interventions) and its cohorts for drill-down."""
    village = villages_col.find_one({"id": village_id}, {"_id": 0})
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")

    is_steward = any(
        m["user_id"] == current_user["id"] and m["village_role"] in ("educator", "elder")
        for m in village.get("members", []))
    if not is_steward and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only the village's stewards see its dashboard")

    member_ids = [m["user_id"] for m in village.get("members", [])]
    scope = {"id": village["id"], "name": village["name"], "member_count": len(member_ids)}
    if not member_ids:
        return {"village": scope, "dimensions": None, "members": [], "attention": [],
                "village_mentors": [], "cohorts": [],
                "message": "No members yet — the dashboard comes alive as the village does."}

    result = _compute_dashboard(member_ids)

    # Mentors of the village, for routing an attention name to a human.
    role_by_user = {m["user_id"]: m["village_role"] for m in village.get("members", [])}
    mentor_ids = [uid for uid, r in role_by_user.items() if r in ("mentor", "elder")]
    village_mentors = [
        users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "picture": 1})
        or {"id": uid, "name": "Unknown"}
        for uid in mentor_ids
    ]

    # Annotate members and attention with how each belongs to this village.
    for m in result["members"]:
        m["village_role"] = role_by_user.get(m["id"])
    for a in result["attention"]:
        a["village_role"] = role_by_user.get(a["id"])

    # Cohort drill-down stays available inside the village view.
    cohorts = [
        {"id": c["id"], "name": c["name"], "member_count": len(c.get("members", []))}
        for c in cohorts_col.find(
            {"id": {"$in": village.get("cohort_ids", [])}},
            {"_id": 0, "id": 1, "name": 1, "members": 1})
    ]

    return {"village": scope, **result, "village_mentors": village_mentors, "cohorts": cohorts}
