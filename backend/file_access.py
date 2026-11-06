"""Who may read a stored file, and the short-lived tokens that prove it.

Why this exists: /api/files/{id}/download and /stream used to authenticate
nobody, so anyone holding a file id could read any course file. This module is
the single rule both routes (and anything that hands out a file URL) consult.

The rule, in order:

1. A file explicitly marked ``visibility: "public"`` is readable by anyone.
   Nothing sets this today; it is the deliberate escape hatch for genuinely
   public assets, so publicness is never an accident of a missing check.
2. Otherwise a signed-in user is required, and they pass when they are:
   - the uploader, or a platform admin;
   - for a submission file: the student who handed it in, or staff on that
     submission's course (same rule as routes/submissions.py);
   - for course material: staff on the owning course (owner, co-teacher, or
     assistant+ — the same rule list_lessons uses), or enrolled in it, and for
     a lesson file the lesson must be open (not hidden, release time passed);
   - for a portfolio file: faculty+ or a linked guardian, when the owner has
     shared the item that holds it.

Course material reaches its course in three ways: the record's own
course_id / lesson_id (attachments and uploaded lesson videos), a lesson whose
``video_file_id`` points at it, or a lesson whose content embeds its URL (PDFs
uploaded from the lesson editor are stored without a course). All three are
checked, cheapest first.

Tags such as <video>, <iframe> and <img> cannot send the X-Session-ID header,
so the browser presents a playback token instead: an HS256 JWT bound to one
user and one file, valid for FILE_TOKEN_TTL seconds (max 600). The access rule
is re-run for the token's user on every request, so un-enrolling someone takes
effect at once rather than when their token expires.
"""

import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from database import (
    courses_col,
    enrollments_col,
    family_links_col,
    lessons_col,
    portfolio_items_col,
    submissions_col,
)
from models.user import UserRole, has_permission

log = logging.getLogger(__name__)

TOKEN_AUDIENCE = "ile-file-access"
MAX_TOKEN_TTL = 600  # ten minutes, the ceiling the design allows
TOKEN_TTL = min(int(os.environ.get("FILE_TOKEN_TTL", str(MAX_TOKEN_TTL))), MAX_TOKEN_TTL)

_SECRET = os.environ.get("FILE_TOKEN_SECRET", "").strip()
if not _SECRET:
    # Tokens only live ten minutes, so a per-process secret is survivable on a
    # single instance: a restart just makes open players fetch a new token.
    # With more than one replica it is not — set FILE_TOKEN_SECRET.
    _SECRET = secrets.token_urlsafe(48)
    log.warning("FILE_TOKEN_SECRET is not set; using a per-process secret. "
                "Set it on every instance so playback tokens verify everywhere.")


# --- tokens -----------------------------------------------------------------

def issue_token(user_id: str, file_id: str, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    exp = now + timedelta(seconds=TOKEN_TTL)
    token = jwt.encode(
        {"sub": user_id, "fid": file_id, "aud": TOKEN_AUDIENCE,
         "iat": int(now.timestamp()), "exp": int(exp.timestamp())},
        _SECRET,
        algorithm="HS256",
    )
    return {"token": token, "expires_at": exp.isoformat()}


def verify_token(token: str, file_id: str) -> Optional[str]:
    """The user id the token was issued to, or None when it is forged,
    expired, or for a different file."""
    try:
        claims = jwt.decode(token, _SECRET, algorithms=["HS256"], audience=TOKEN_AUDIENCE)
    except jwt.InvalidTokenError:
        return None
    if claims.get("fid") != file_id or not claims.get("sub"):
        return None
    return claims["sub"]


def signed_path(file_id: str, user_id: str, kind: str = "download") -> str:
    """A ready-to-use relative URL carrying a fresh token for this user."""
    return f"/api/files/{file_id}/{kind}?t={issue_token(user_id, file_id)['token']}"


# --- the access rule --------------------------------------------------------

def is_public(file_data: dict) -> bool:
    return file_data.get("visibility") == "public"


def _is_staff_on(course: dict, user: dict) -> bool:
    from routes.courses import _is_course_staff  # lazy: courses imports a lot
    return _is_course_staff(course, user) or has_permission(user["role"], UserRole.ASSISTANT)


def _is_enrolled(course_id: str, user_id: str) -> bool:
    return enrollments_col.find_one({"user_id": user_id, "course_id": course_id}) is not None


def _owning_lessons(file_data: dict) -> list:
    fid = file_data["id"]
    if file_data.get("lesson_id"):
        lesson = lessons_col.find_one({"id": file_data["lesson_id"]})
        if lesson:
            return [lesson]
    found = list(lessons_col.find({"video_file_id": fid}))
    if found:
        return found
    # Embedded from the lesson editor: only the lesson's content knows.
    return list(lessons_col.find({"content": {"$regex": re.escape(fid)}}))


def _course_access(file_data: dict, user: dict) -> bool:
    from routes.courses import _lesson_is_open

    lessons = _owning_lessons(file_data)
    targets = [(l.get("course_id"), l) for l in lessons]
    if not targets and file_data.get("course_id"):
        targets = [(file_data["course_id"], None)]  # course-level attachment

    for course_id, lesson in targets:
        course = courses_col.find_one({"id": course_id}) if course_id else None
        if not course:
            continue
        if _is_staff_on(course, user):
            return True
        if _is_enrolled(course_id, user["id"]) and (lesson is None or _lesson_is_open(lesson)):
            return True
    return False


def _submission_access(file_data: dict, user: dict) -> bool:
    submission = submissions_col.find_one({"id": file_data["submission_id"]})
    if not submission:
        return False
    if submission.get("student_id") == user["id"]:
        return True
    course = courses_col.find_one({"id": submission.get("course_id")})
    if not course:
        return False
    from routes.courses import _is_course_staff
    return _is_course_staff(course, user) or has_permission(user["role"], UserRole.FACULTY)


def _portfolio_access(file_data: dict, user: dict) -> bool:
    for item in portfolio_items_col.find({"file_id": file_data["id"], "visibility": "shared"}):
        if has_permission(user["role"], UserRole.FACULTY):
            return True
        if family_links_col.find_one({"guardian_id": user["id"], "youth_id": item.get("user_id")}):
            return True
    return False


def can_access(file_data: dict, user: Optional[dict]) -> bool:
    if is_public(file_data):
        return True
    if not user:
        return False
    if file_data.get("uploaded_by") == user["id"] or user.get("role") == UserRole.ADMIN:
        return True
    if file_data.get("submission_id"):
        # Student work never falls through to the course rule.
        return _submission_access(file_data, user)
    if _course_access(file_data, user):
        return True
    return _portfolio_access(file_data, user)
