"""Course access end dates (item I6).

A course's access lasts forever (the default) or until a date the organizer
sets: ``course.access_ends_at``. Staff can override it for one person:
``enrollment.access_ends_at``. Whether that key is present decides:

    key absent                -> follow the course (this is every enrollment
                                 by default, including I1 imports, so changing
                                 the course date moves everyone with it)
    key present, value None   -> this person keeps access forever
    key present, a datetime   -> this person's own end date

After the end, a student keeps the course page and their certificate, but
lesson content, files, video, quizzes, comments, discussions and submissions
refuse with 403 ``access_ended:<ISO date>`` (the same "code:value" shape the
app already parses for tier limits). Course staff are never affected.

This module reads no database; callers pass the course and enrollment in.

An end date that can't be read counts as ended: withholding beats leaking,
the same rule as scheduled lesson release. The setters below only ever store
real datetimes, so this only matters for hand-edited records.
"""

from datetime import datetime, time, timezone
from typing import Optional

from fastapi import HTTPException

# Pure rules: callers look up the course and enrollment and pass them in.

ENDED_CODE = "access_ended"
_UNREADABLE = datetime.min.replace(tzinfo=timezone.utc)


def parse_end(value):
    """API input → aware datetime, or None for "forever".

    Accepts an ISO datetime (with or without zone; no zone means UTC) or a
    plain date, which means the end of that day in UTC. Raises ValueError for
    anything else."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        raise ValueError("access_ends_at must be a date, a date and time, or null")
    text = value.strip()
    try:
        if len(text) == 10:
            day = datetime.fromisoformat(text).date()
            return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("access_ends_at must be a date, a date and time, or null")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _stored(value):
    """A stored end date → aware datetime, None for forever, _UNREADABLE when
    it can't be read."""
    if value is None:
        return None
    try:
        return parse_end(value)
    except ValueError:
        return _UNREADABLE


def effective_end(course: dict, enrollment: Optional[dict]):
    """When this person's access ends, or None for never."""
    if enrollment is not None and "access_ends_at" in enrollment:
        return _stored(enrollment["access_ends_at"])
    return _stored((course or {}).get("access_ends_at"))


def ended_at(course: dict, enrollment: Optional[dict], now: datetime = None):
    """The end date if it has passed, else None."""
    if enrollment and enrollment.get("iap_managed") and enrollment.get("iap_revoked_at"):
        return _stored(enrollment["iap_revoked_at"])
    end = effective_end(course, enrollment)
    if end is None:
        return None
    return end if end <= (now or datetime.now(timezone.utc)) else None


def course_ended(course: dict, now: datetime = None) -> bool:
    """The course-wide date has passed (for joining: you can't sign up to a
    course whose access period is over)."""
    return ended_at(course, None, now) is not None


def detail(end: datetime) -> str:
    if end == _UNREADABLE:
        return f"{ENDED_CODE}:"
    return f"{ENDED_CODE}:{end.isoformat()}"


def require_open(course: dict, enrollment: Optional[dict], now: datetime = None):
    """Raise 403 access_ended for an enrollment whose access is over."""
    end = ended_at(course, enrollment, now)
    if end is not None:
        raise HTTPException(status_code=403, detail=detail(end))


def viewer_access(course: dict, enrollment: Optional[dict], now: datetime = None) -> dict:
    """What the course page shows an enrolled person about their access."""
    end = effective_end(course, enrollment)
    over = ended_at(course, enrollment, now) is not None
    return {
        "access_ends_at": None if end in (None, _UNREADABLE) else end.isoformat(),
        "access_ended": over,
        "overridden": enrollment is not None and "access_ends_at" in enrollment,
    }


def serialize_end(course_or_enrollment: dict):
    end = _stored(course_or_enrollment.get("access_ends_at"))
    return None if end in (None, _UNREADABLE) else end.isoformat()
