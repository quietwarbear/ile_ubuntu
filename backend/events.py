"""Activity event stream — the typed record of meaningful actions on the platform.

This is the substrate for analytics-at-scale (aggregation pipelines over indexed
events instead of in-memory collection scans) and, later, the Ubuntu Intelligence
layer (§7 of the June 2026 product evaluation).

Design rules:
- emit() is fire-and-forget: it must NEVER raise or add meaningful latency to the
  request path. A lost event is acceptable; a failed user action is not.
- Events are append-only and never deleted (no TTL) — they are the long-term record.
- Event types are namespaced strings: "<domain>.<action>", lowercase, past tense
  where natural. Add new types to EVENT_TYPES so the taxonomy stays discoverable.
"""

import logging
import uuid
from datetime import datetime, timezone

from database import events_col

logger = logging.getLogger(__name__)

# Canonical taxonomy. Not enforced at write time (events must never fail),
# but emit() warns on unknown types so drift is visible in logs.
EVENT_TYPES = {
    # auth
    "user.registered",
    "user.logged_in",
    "user.deleted",
    "user.password_reset",
    "user.onboarded",
    # family / minor safety
    "family.linked",
    "family.unlinked",
    "family.digest_sent",
    # learning circles (reciprocal co-learner pairings)
    "circle.formed",
    "circle.ended",
    "circle.goal_added",
    "circle.goal_completed",
    "circle.note_added",
    # wellness (the event never carries scores — see routes/checkins.py)
    "wellness.checked_in",
    # personal portfolio + individual goals (no titles/content in meta)
    "portfolio.item_added",
    "portfolio.item_removed",
    "goal.set",
    "goal.completed",
    # village
    "village.created",
    "village.member_added",
    "village.member_removed",
    "village.goal_added",
    "village.goal_completed",
    "village.course_attached",
    "village.session_attached",
    "village.session_held",
    "village.goal_progress",
    # learning
    "course.created",
    "course.enrolled",
    "course.unenrolled",
    "lesson.completed",
    "course.completed",
    "quiz.attempted",
    "certificate.issued",
    "course.purchased",
    # live teaching
    "live_session.started",
    "live_session.ended",
    "live_session.joined",
    "attendance.recorded",
    # community
    "post.created",
    "post.replied",
    "post.liked",
    "lesson.commented",
    # belonging containers
    "cohort.joined",
    "cohort.left",
    "space.access_requested",
    "space.access_approved",
    # monetization
    "subscription.activated",
    "subscription.cancelled",
}


def emit(event_type: str, user: dict | None = None, entity_type: str | None = None,
         entity_id: str | None = None, meta: dict | None = None):
    """Record a typed activity event. Never raises."""
    try:
        if event_type not in EVENT_TYPES:
            logger.warning("emit(): unknown event type %r — add it to EVENT_TYPES", event_type)
        events_col.insert_one({
            "id": str(uuid.uuid4()),
            "type": event_type,
            "user_id": (user or {}).get("id"),
            "user_role": (user or {}).get("role"),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        # A lost event must never break the user-facing action.
        logger.exception("emit(%s) failed", event_type)
