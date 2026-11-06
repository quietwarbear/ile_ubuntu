"""Bulk enrollment from a roster (item I1).

An organizer hands over one CSV of the people registered for an event and
which sessions (days) each person attends. Each session maps to one course.
This module turns that file into accounts and enrollments.

It is a service, not a route: routes/enrollment_imports.py calls it for the
CSV upload, and the later Kindred → Ile Ubuntu handoff (X2) can call
import_enrollments() directly with rows it already holds.

Rules
- Accounts that don't exist are created with no password, marked invited
  (auth_provider "invited"). They get in by setting a password through the
  reset-password email, or by signing in with Google/Apple on that address.
  Existing accounts are never changed.
- Each person is enrolled free into exactly the courses their row lists.
  Imported enrollments skip tier limits and premium pricing, and they don't
  count toward the person's own tier limit (source "import").
- Private courses (I2) are the point: an import is one of the only two ways
  in. Only the course's own staff (owner, co-teachers, platform admins) can
  import into it; to anyone else a course they don't run is "unknown", so an
  import can't be used to probe which private courses exist.
- Idempotent. Emails are trimmed and lower-cased; a rerun with added rows
  enrolls only the new people/courses. No duplicate users or enrollments
  (both writes are upserts on their natural keys).
- A row with any problem (bad email, no sessions, a session that doesn't
  resolve) is rejected whole and reported, so nothing is half-done; fix the
  file or the mapping and run it again.
- Everyone newly enrolled gets one welcome email (I3) naming the course(s)
  they were just added to, with a single-use sign-in link (email_signin.py).
  A rerun that adds nothing sends nothing; a dry run never sends. Emails go
  out paced on one background thread (Resend's rate limit).
"""

import csv
import io
import re
import uuid
from datetime import datetime, timezone

from database import courses_col, enrollments_col, users_col
from events import emit
from models.user import UserRole

IMPORT_SOURCE = "import"
MAX_ROWS = 5000
MAX_CSV_CHARS = 2_000_000

# Several sessions in one cell are separated by ";" or "|" (or a line break).
# Not commas: session labels like "Saturday, June 6" contain them.
_SESSION_SPLIT = re.compile(r"[;|\n]")
_EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")

HEADER_ALIASES = {
    "name": ("name", "full name", "full_name", "fullname"),
    "email": ("email", "email address", "e-mail", "email_address"),
    "sessions": ("sessions", "session", "days", "day", "courses", "course"),
}


class BulkImportError(ValueError):
    """The whole file can't be used (missing columns, too large)."""


def normalize_email(raw) -> str:
    return (raw or "").strip().lower()


def _clean_sessions(raw) -> list:
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = _SESSION_SPLIT.split(raw or "")
    seen, out = set(), []
    for part in parts:
        label = str(part).strip()
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def parse_roster_csv(text: str) -> dict:
    """Read the roster. Returns {"rows": [...], "errors": [...]}.

    Row numbers match the spreadsheet: the header is row 1.
    """
    if text is None:
        text = ""
    if len(text) > MAX_CSV_CHARS:
        raise BulkImportError("The file is too large. Split it into smaller files.")
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise BulkImportError("The file is empty.")
    except csv.Error as exc:
        raise BulkImportError(f"The file isn't readable as CSV: {exc}")

    columns = {}
    for index, title in enumerate(header):
        key = (title or "").strip().lower()
        for field, aliases in HEADER_ALIASES.items():
            if key in aliases and field not in columns:
                columns[field] = index
    missing = [f for f in ("email", "sessions") if f not in columns]
    if missing:
        raise BulkImportError(
            "The file needs a header row with these columns: name, email, sessions "
            f"(missing: {', '.join(missing)})."
        )

    def cell(values, field):
        i = columns.get(field)
        return values[i] if i is not None and i < len(values) else ""

    rows, errors = [], []
    try:
        for row_number, values in enumerate(reader, start=2):
            if not any((v or "").strip() for v in values):
                continue
            if len(rows) + len(errors) >= MAX_ROWS:
                raise BulkImportError(f"The file has more than {MAX_ROWS} people. Split it into smaller files.")
            email = normalize_email(cell(values, "email"))
            name = (cell(values, "name") or "").strip()
            sessions = _clean_sessions(cell(values, "sessions"))
            if not _EMAIL_RE.match(email):
                errors.append({"row": row_number, "email": email, "error": "Missing or invalid email"})
                continue
            if not sessions:
                errors.append({"row": row_number, "email": email, "error": "No sessions listed"})
                continue
            rows.append({"row": row_number, "name": name, "email": email, "sessions": sessions})
    except csv.Error as exc:
        raise BulkImportError(f"The file isn't readable as CSV: {exc}")
    return {"rows": rows, "errors": errors}


def session_labels(rows: list) -> list:
    """Every distinct session label in the rows, in first-seen order."""
    seen, out = set(), []
    for row in rows:
        for label in row.get("sessions", []):
            if label not in seen:
                seen.add(label)
                out.append(label)
    return out


def is_course_staff(course: dict, actor: dict) -> bool:
    """Owner, co-teacher, or platform admin — the same people who can add one
    student by email (routes/courses.py _is_course_staff). Platform-wide
    faculty reach is deliberately not enough."""
    staff = [course.get("instructor_id")] + list(course.get("co_instructor_ids") or [])
    return actor.get("id") in staff or actor.get("role") == UserRole.ADMIN


def importable_courses(actor: dict) -> list:
    """Courses this person can import into."""
    projection = {"_id": 0, "id": 1, "title": 1, "visibility": 1, "status": 1}
    if actor.get("role") == UserRole.ADMIN:
        query = {}
    else:
        query = {"$or": [{"instructor_id": actor["id"]}, {"co_instructor_ids": actor["id"]}]}
    return list(courses_col.find(query, projection).sort("title", 1))


def suggest_mapping(labels: list, actor: dict) -> dict:
    """Pre-fill the mapping: a label that is a course id, or exactly a course
    title (ignoring case), of a course this person runs."""
    courses = importable_courses(actor)
    by_id = {c["id"]: c["id"] for c in courses}
    by_title = {}
    for c in courses:
        by_title.setdefault((c.get("title") or "").strip().lower(), c["id"])
    return {
        label: by_id.get(label) or by_title.get(label.strip().lower())
        for label in labels
    }


def _find_user(email: str):
    user = users_col.find_one({"email": email}, {"_id": 0})
    if user:
        return user
    # Older accounts may have been stored with capitals.
    return users_col.find_one(
        {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}, {"_id": 0}
    )


def _send_welcome_emails(people) -> int:
    """Queue one welcome email per person. Returns how many were queued.
    Failures are logged (email_log) and never undo the enrollments."""
    import email_signin
    from routes.email_notifications import send_paced_in_background

    messages = []
    for user, titles in people:
        if not user.get("email"):
            continue
        token = email_signin.issue_token(user["id"], "welcome")
        subject, html = email_signin.welcome_email(
            user.get("name", ""), titles, email_signin.signin_url(token)
        )
        messages.append((user["email"], subject, html, "welcome"))
    send_paced_in_background(messages)
    return len(messages)


def import_enrollments(rows: list, session_map: dict = None, actor: dict = None,
                       *, dry_run: bool = False, send_welcome: bool = True) -> dict:
    """Create invited accounts and enroll each row into its sessions' courses.

    rows: [{"row": n, "name": str, "email": str, "sessions": [label, ...]}]
          (the shape parse_roster_csv returns; "row" is optional)
    session_map: {label: course_id}. A label not in the map is tried as a
          course id.
    actor: the person running the import. They must be staff on every course
          a row names. None means a trusted internal caller (such as X2's
          authenticated handoff) that has already authorized itself.
    dry_run: work out the report without writing anything (the preview).
    send_welcome: email each newly enrolled person (never in a dry run).
    """
    session_map = {str(k).strip(): v for k, v in (session_map or {}).items() if v}
    now = datetime.now(timezone.utc)
    report = {"dry_run": dry_run, "created": [], "enrolled": [], "skipped": [], "errors": []}
    course_cache = {}
    known_users = {}        # email -> user (or a planned user in a dry run)
    done_pairs = set()      # (email, course_id) handled earlier in this file
    touched_courses = set()
    new_by_user = {}        # user id -> (user, [course titles enrolled now])

    def resolve(label):
        if label in course_cache:
            return course_cache[label]
        course_id = session_map.get(label) or label
        course = courses_col.find_one({"id": course_id}, {"_id": 0})
        if course and actor is not None and not is_course_staff(course, actor):
            course = None   # indistinguishable from not existing
        course_cache[label] = course
        return course

    for index, raw in enumerate(rows):
        row_number = raw.get("row") or index + 1
        email = normalize_email(raw.get("email"))
        name = (raw.get("name") or "").strip()
        labels = _clean_sessions(raw.get("sessions"))
        if not _EMAIL_RE.match(email):
            report["errors"].append({"row": row_number, "email": email, "error": "Missing or invalid email"})
            continue
        if not labels:
            report["errors"].append({"row": row_number, "email": email, "error": "No sessions listed"})
            continue
        unknown = [label for label in labels if resolve(label) is None]
        if unknown:
            report["errors"].append({
                "row": row_number, "email": email,
                "error": "Unknown session: " + ", ".join(unknown),
            })
            continue
        courses = []
        for label in labels:
            course = resolve(label)
            if course["id"] not in {c["id"] for c in courses}:
                courses.append(course)

        user = known_users.get(email) or _find_user(email)
        created = False
        if not user:
            created = True
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "name": name or email.split("@")[0],
                "picture": "",
                "role": UserRole.STUDENT,
                "bio": "",
                "auth_provider": "invited",
                "invited": True,
                "invited_at": now,
                "invited_by": (actor or {}).get("id"),
                "email_verified": False,
                "created_at": now,
            }
            if not dry_run:
                result = users_col.update_one({"email": email}, {"$setOnInsert": user}, upsert=True)
                if result.upserted_id is None:
                    user = _find_user(email)   # someone else created it just now
                    created = False
                else:
                    emit("user.invited", actor, "user", user["id"], meta={"source": IMPORT_SOURCE})
            if created:
                report["created"].append({"row": row_number, "email": email, "name": user["name"]})
        known_users[email] = user

        for course in courses:
            entry = {"row": row_number, "email": email,
                     "course_id": course["id"], "course_title": course.get("title", "")}
            pair = (email, course["id"])
            if pair in done_pairs:
                report["skipped"].append({**entry, "reason": "Listed twice in this file"})
                continue
            done_pairs.add(pair)
            existing = enrollments_col.find_one({"user_id": user["id"], "course_id": course["id"]})
            if existing:
                report["skipped"].append({**entry, "reason": "Already enrolled"})
                continue
            if not dry_run:
                enrollment = {
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "user_name": user.get("name", "Learner"),
                    "course_id": course["id"],
                    "enrolled_at": now,
                    "completed_lessons": [],
                    "progress": 0.0,
                    "status": "active",
                    "completed_at": None,
                    "source": IMPORT_SOURCE,
                    "added_by": (actor or {}).get("id"),
                }
                result = enrollments_col.update_one(
                    {"user_id": user["id"], "course_id": course["id"]},
                    {"$setOnInsert": enrollment},
                    upsert=True,
                )
                if result.upserted_id is None:
                    report["skipped"].append({**entry, "reason": "Already enrolled"})
                    continue
                touched_courses.add(course["id"])
                new_by_user.setdefault(user["id"], (user, []))[1].append(course.get("title", ""))
                emit("course.enrolled", actor, "course", course["id"],
                     meta={"student_id": user["id"], "source": IMPORT_SOURCE})
            report["enrolled"].append(entry)

    # Recount rather than increment, so a rerun or a race can't drift it.
    for course_id in touched_courses:
        courses_col.update_one(
            {"id": course_id},
            {"$set": {"enrolled_count": enrollments_col.count_documents({"course_id": course_id})}},
        )

    report["welcome_emails"] = 0
    if send_welcome and not dry_run and new_by_user:
        report["welcome_emails"] = _send_welcome_emails(new_by_user.values())

    report["errors"].sort(key=lambda e: e["row"])
    report["counts"] = {key: len(report[key]) for key in ("created", "enrolled", "skipped", "errors")}
    return report
