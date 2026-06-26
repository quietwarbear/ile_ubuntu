"""Family ecosystem v1 — guardian <-> youth linkage (minor-safety foundation).

How linking works: a learner (typically a young person) has a family code on
their account. A guardian enters that code on the Family page and becomes
linked. Either side can remove the link. Guardians see a warm growth summary
of their young person — progress and activity, not raw grades.

This is the technical foundation, not legal compliance: review COPPA/FERPA
posture with counsel before marketing to under-13s.
"""

import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from database import users_col, family_links_col, enrollments_col, courses_col, events_col, villages_col
from middleware import get_current_user
from events import emit

router = APIRouter(prefix="/api/family", tags=["family"])

_PUBLIC_USER = {"_id": 0, "id": 1, "name": 1, "picture": 1, "is_minor": 1}


def _user_brief(uid: str) -> dict:
    u = users_col.find_one({"id": uid}, _PUBLIC_USER) or {"id": uid, "name": "Unknown"}
    return u


def is_guardian_of(guardian_id: str, youth_id: str) -> bool:
    return family_links_col.find_one({"guardian_id": guardian_id, "youth_id": youth_id}) is not None


@router.get("")
def my_family(current_user: dict = Depends(get_current_user)):
    """Both sides of my family graph + my family code."""
    guardians = [
        {**_user_brief(l["guardian_id"]), "linked_at": l.get("created_at")}
        for l in family_links_col.find({"youth_id": current_user["id"]}, {"_id": 0})
    ]
    youth = [
        {**_user_brief(l["youth_id"]), "linked_at": l.get("created_at")}
        for l in family_links_col.find({"guardian_id": current_user["id"]}, {"_id": 0})
    ]
    return {
        "family_code": current_user.get("family_code"),
        "guardians": guardians,
        "youth": youth,
    }


@router.post("/code")
def generate_family_code(current_user: dict = Depends(get_current_user)):
    """Create (or rotate) my family code. Rotating invalidates the old code
    for NEW links; existing links remain."""
    code = secrets.token_urlsafe(5)[:6].replace("_", "x").replace("-", "y").upper()
    users_col.update_one({"id": current_user["id"]}, {"$set": {"family_code": code}})
    return {"family_code": code}


@router.post("/link")
async def link_youth(request: Request, current_user: dict = Depends(get_current_user)):
    """Redeem a family code: the current user becomes a guardian of its owner."""
    data = await request.json()
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Family code required")

    youth = users_col.find_one({"family_code": code})
    if not youth:
        raise HTTPException(status_code=404, detail="That code doesn't match anyone. Double-check it with your young person.")
    if youth["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="That's your own code")
    if is_guardian_of(current_user["id"], youth["id"]):
        return {"success": True, "message": "Already linked", "youth": _user_brief(youth["id"])}

    family_links_col.insert_one({
        "id": str(uuid.uuid4()),
        "guardian_id": current_user["id"],
        "youth_id": youth["id"],
        "code_used": code,
        "created_at": datetime.now(timezone.utc),
    })
    emit("family.linked", current_user, "user", youth["id"])
    return {"success": True, "youth": _user_brief(youth["id"])}


@router.delete("/link/{other_id}")
def unlink(other_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a family link from either side."""
    result = family_links_col.delete_one({
        "$or": [
            {"guardian_id": current_user["id"], "youth_id": other_id},
            {"guardian_id": other_id, "youth_id": current_user["id"]},
        ]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No such family link")
    emit("family.unlinked", current_user, "user", other_id)
    return {"success": True}


def _build_youth_summary(youth_id: str) -> dict:
    """Growth summary data: progress and participation, told warmly."""
    youth = _user_brief(youth_id)

    enrollments = []
    for e in enrollments_col.find({"user_id": youth_id}, {"_id": 0, "course_id": 1, "progress": 1, "status": 1}):
        course = courses_col.find_one({"id": e["course_id"]}, {"_id": 0, "title": 1})
        enrollments.append({
            "course_title": (course or {}).get("title", "A course"),
            "progress": round(e.get("progress", 0)),
            "completed": e.get("status") == "completed",
        })

    since = datetime.now(timezone.utc) - timedelta(days=7)
    week_counts = {}
    pipeline = [
        {"$match": {"user_id": youth_id, "created_at": {"$gte": since}}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
    ]
    for row in events_col.aggregate(pipeline):
        week_counts[row["_id"]] = row["count"]

    # Their village (Phase 3: measures go village-wide). First village if
    # several — the digest is a warm note, not an exhaustive report.
    village = villages_col.find_one(
        {"members.user_id": youth_id},
        {"_id": 0, "id": 1, "name": 1, "season": 1, "goals": 1})
    village_info = None
    if village:
        goals = village.get("goals", [])
        village_info = {
            "name": village["name"],
            "season": village.get("season", ""),
            "goals_done": sum(1 for g in goals if g.get("done")),
            "goals_total": len(goals),
        }

    return {
        "youth": youth,
        "village": village_info,
        "enrollments": enrollments,
        "this_week": {
            "lessons_completed": week_counts.get("lesson.completed", 0),
            "live_sessions_joined": week_counts.get("live_session.joined", 0),
            "posts_and_replies": week_counts.get("post.created", 0) + week_counts.get("post.replied", 0),
            "quizzes_attempted": week_counts.get("quiz.attempted", 0),
            "courses_completed": week_counts.get("course.completed", 0),
        },
    }


@router.get("/youth/{youth_id}/summary")
def youth_summary(youth_id: str, current_user: dict = Depends(get_current_user)):
    """Guardian-only growth summary. Not a gradebook."""
    if not is_guardian_of(current_user["id"], youth_id):
        raise HTTPException(status_code=403, detail="You're not linked to this young person")
    return _build_youth_summary(youth_id)


# --- Weekly family digest (eval mid-term: the ClassDojo loop, with dignity) ---

import os

DIGEST_SECRET = os.environ.get("DIGEST_SECRET", "")


def _digest_section_html(s: dict) -> str:
    """One youth's section of the digest email."""
    w = s["this_week"]
    name = s["youth"].get("name", "Your young person")
    first = name.split(" ")[0]

    lines = []
    if w["lessons_completed"]:
        lines.append(f"completed {w['lessons_completed']} lesson{'s' if w['lessons_completed'] != 1 else ''}")
    if w["live_sessions_joined"]:
        lines.append(f"joined {w['live_sessions_joined']} live session{'s' if w['live_sessions_joined'] != 1 else ''}")
    if w["posts_and_replies"]:
        lines.append(f"contributed {w['posts_and_replies']} time{'s' if w['posts_and_replies'] != 1 else ''} in the community")
    if w["quizzes_attempted"]:
        lines.append(f"took on {w['quizzes_attempted']} quiz{'zes' if w['quizzes_attempted'] != 1 else ''}")
    if w["courses_completed"]:
        lines.append(f"<strong style='color:#D4AF37'>finished {w['courses_completed']} whole course{'s' if w['courses_completed'] != 1 else ''}</strong>")

    if lines:
        week_html = f"<p>This week, {first} " + ", ".join(lines) + ".</p>"
    else:
        week_html = (f"<p>{first} had a quiet week on the platform. A word of encouragement "
                     f"from you can mean more than you know.</p>")

    journey = ""
    active = [e for e in s["enrollments"] if not e["completed"]][:3]
    done = [e for e in s["enrollments"] if e["completed"]]
    if active:
        rows = "".join(
            f"<li>{e['course_title']} — {e['progress']}% of the way</li>" for e in active
        )
        journey += f"<p style='margin-bottom:4px'>On the journey:</p><ul style='margin-top:0'>{rows}</ul>"
    if done:
        journey += f"<p>Already carried home: {', '.join(e['course_title'] for e in done)}. 🏆</p>"

    # Their village walks with them (Phase 3): name + collective goal progress.
    village_html = ""
    v = s.get("village")
    if v:
        if v["goals_total"]:
            village_html = (
                f"<p style='color:#94A3B8'>{first}'s village, <strong style='color:#D4AF37'>{v['name']}</strong>, "
                f"has carried home {v['goals_done']} of {v['goals_total']} goals"
                f"{' this ' + v['season'] if v['season'] else ' this season'}.</p>")
        else:
            village_html = (
                f"<p style='color:#94A3B8'>{first} belongs to the "
                f"<strong style='color:#D4AF37'>{v['name']}</strong> village.</p>")

    return (f"<h3 style='color:#D4AF37;font-size:15px;margin:18px 0 6px'>{name}</h3>"
            f"{week_html}{village_html}{journey}")


def _send_guardian_digest(guardian: dict, youth_ids: list) -> bool:
    """Build and send one guardian's digest. Returns True if sent."""
    import asyncio
    from routes.email_notifications import send_email, build_email_html

    email = guardian.get("email")
    if not email:
        return False

    sections = "".join(_digest_section_html(_build_youth_summary(yid)) for yid in youth_ids)
    html = build_email_html(
        "How your young people showed up this week",
        f"<p>Hello, <strong>{guardian.get('name', '')}</strong>. Here's this week's note from the village:</p>"
        + sections
        + "<p style='margin-top:16px'>Thank you for walking with them. — The Ile Ubuntu</p>",
        "Open the Family Page",
        "https://www.ile-ubuntu.org/family",
    )
    asyncio.run(send_email(email, "This week in the village — The Ile Ubuntu", html))
    return True


def _week_key() -> str:
    now = datetime.now(timezone.utc).isocalendar()
    return f"{now[0]}-W{now[1]:02d}"


@router.post("/digest/run")
def run_weekly_digest(request: Request):
    """Send the weekly digest to every guardian. Idempotent per guardian per
    ISO week — safe to trigger repeatedly. Auth: X-Digest-Key header."""
    from database import digest_log_col
    from pymongo.errors import DuplicateKeyError

    if not DIGEST_SECRET or request.headers.get("X-Digest-Key") != DIGEST_SECRET:
        raise HTTPException(status_code=401, detail="Invalid digest key")

    week = _week_key()
    by_guardian = {}
    for link in family_links_col.find({}, {"_id": 0, "guardian_id": 1, "youth_id": 1}):
        by_guardian.setdefault(link["guardian_id"], []).append(link["youth_id"])

    sent, skipped = 0, 0
    for guardian_id, youth_ids in by_guardian.items():
        try:
            digest_log_col.insert_one({
                "guardian_id": guardian_id,
                "week_key": week,
                "youth_count": len(youth_ids),
                "sent_at": datetime.now(timezone.utc),
            })
        except DuplicateKeyError:
            skipped += 1
            continue
        guardian = users_col.find_one({"id": guardian_id}) or {}
        if _send_guardian_digest(guardian, youth_ids):
            emit("family.digest_sent", {"id": guardian_id}, meta={"week": week, "youth": len(youth_ids)})
            sent += 1

    return {"week": week, "sent": sent, "already_sent": skipped, "guardians": len(by_guardian)}


@router.post("/digest/preview")
def preview_digest(current_user: dict = Depends(get_current_user)):
    """Send ME my digest right now (no idempotency — it's a preview)."""
    youth_ids = [l["youth_id"] for l in family_links_col.find({"guardian_id": current_user["id"]}, {"_id": 0, "youth_id": 1})]
    if not youth_ids:
        raise HTTPException(status_code=400, detail="No linked young people yet")
    if not _send_guardian_digest(current_user, youth_ids):
        raise HTTPException(status_code=400, detail="Your account has no email address")
    return {"success": True, "message": "Preview sent — check your inbox"}
