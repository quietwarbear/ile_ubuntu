"""Kindred → Ile Ubuntu handoff (item X2).

After an event, an organizer in Kindred sends the people who came, with the
activities each was marked coming for, and Ile Ubuntu enrolls them through the
same roster import as a CSV upload (bulk_enrollment.import_enrollments): same
idempotency, same report, same welcome email with a sign-in link (I3). No
shared login is needed.

Two things have to be true before anyone is enrolled:

1. The request really comes from Kindred's server. Kindred signs every call
   with a secret both services hold (KINDRED_HANDOFF_SECRET here):
       X-Handoff-Timestamp: <unix seconds>
       X-Handoff-Signature: v1=<hex HMAC-SHA256(secret, "<timestamp>.<raw body>")>
   Requests older or newer than five minutes are refused. A replay inside that
   window can only repeat an import, which is idempotent.

2. The organizer is allowed to enroll people into those courses. A shared
   secret alone would let any Kindred organizer fill any Ile Ubuntu course,
   private ones included (I2). So the course's own teacher issues a
   connection key here (shown once) and gives it to the organizer, who pastes
   it into Kindred. Each call carries the key; the import runs as the teacher
   who issued it, so I1's rule holds unchanged: only a course's staff
   (owner, co-teachers, platform admins) can import into it, and a course
   they don't run is reported as unknown. Only the key's SHA-256 hash is
   stored. Issuing a new key revokes the previous one; revoking cuts Kindred
   off at once.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone

from database import kindred_handoff_keys_col, users_col

SIGNATURE_VERSION = "v1"
MAX_SKEW_SECONDS = 300
KEY_PREFIX = "kh_"
MAX_ROWS = 5000


class HandoffAuthError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def handoff_secret() -> str:
    return os.environ.get("KINDRED_HANDOFF_SECRET", "").strip()


def sign(secret: str, timestamp: str, body: bytes) -> str:
    """The signature Kindred sends. Kept here so tests and docs share it."""
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"{SIGNATURE_VERSION}={mac.hexdigest()}"


def verify_signature(timestamp: str | None, signature: str | None, body: bytes,
                     *, secret: str | None = None, now: float | None = None) -> None:
    secret = handoff_secret() if secret is None else secret
    if not secret:
        raise HandoffAuthError(503, "The Kindred handoff is not set up on this server.")
    if not timestamp or not signature:
        raise HandoffAuthError(401, "Missing signature.")
    try:
        sent = int(timestamp)
    except ValueError:
        raise HandoffAuthError(401, "Bad signature.")
    now = time.time() if now is None else now
    if abs(now - sent) > MAX_SKEW_SECONDS:
        raise HandoffAuthError(401, "Signature expired.")
    expected = sign(secret, timestamp, body)
    if not hmac.compare_digest(expected.encode(), signature.strip().encode()):
        raise HandoffAuthError(401, "Bad signature.")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def issue_key(user: dict, now: datetime | None = None) -> str:
    """Create a connection key for this person (revoking any earlier one).
    Returns the raw key; it is never stored or shown again."""
    now = now or datetime.now(timezone.utc)
    kindred_handoff_keys_col.update_many(
        {"user_id": user["id"], "revoked_at": None},
        {"$set": {"revoked_at": now}},
    )
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    kindred_handoff_keys_col.insert_one({
        "key_hash": _hash(key),
        "user_id": user["id"],
        "last4": key[-4:],
        "created_at": now,
        "revoked_at": None,
        "last_used_at": None,
    })
    return key


def key_status(user: dict) -> dict:
    record = kindred_handoff_keys_col.find_one(
        {"user_id": user["id"], "revoked_at": None}, {"_id": 0, "key_hash": 0}
    )
    if not record:
        return {"active": False}
    return {
        "active": True,
        "last4": record.get("last4", ""),
        "created_at": record.get("created_at"),
        "last_used_at": record.get("last_used_at"),
    }


def revoke_key(user: dict, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    result = kindred_handoff_keys_col.update_many(
        {"user_id": user["id"], "revoked_at": None}, {"$set": {"revoked_at": now}}
    )
    return result.modified_count


def resolve_key(key: str | None, now: datetime | None = None) -> dict:
    """The teacher this key acts for. Unknown, revoked and malformed keys are
    all refused the same way."""
    if not isinstance(key, str) or not key.startswith(KEY_PREFIX) or len(key) > 200:
        raise HandoffAuthError(403, "This connection key isn't valid. Ask the course's teacher for a new one.")
    record = kindred_handoff_keys_col.find_one({"key_hash": _hash(key.strip()), "revoked_at": None})
    user = users_col.find_one({"id": record["user_id"]}, {"_id": 0}) if record else None
    if not user:
        raise HandoffAuthError(403, "This connection key isn't valid. Ask the course's teacher for a new one.")
    kindred_handoff_keys_col.update_one(
        {"key_hash": record["key_hash"]},
        {"$set": {"last_used_at": now or datetime.now(timezone.utc)}},
    )
    return user


def rows_from_attendees(attendees) -> tuple[list, list]:
    """Turn Kindred's attendee list into import rows.

    attendees: [{"name": str, "email": str, "course_ids": [str, ...]}]
    Each course id is passed straight to the import as a session label, which
    the import resolves as a course id and checks the teacher runs it.
    """
    if not isinstance(attendees, list):
        raise HandoffAuthError(400, "attendees must be a list.")
    if len(attendees) > MAX_ROWS:
        raise HandoffAuthError(413, f"Send at most {MAX_ROWS} people at a time.")
    rows, errors = [], []
    for index, person in enumerate(attendees, start=1):
        if not isinstance(person, dict):
            errors.append({"row": index, "email": "", "error": "Not a person record"})
            continue
        course_ids = person.get("course_ids")
        if not isinstance(course_ids, list):
            course_ids = []
        rows.append({
            "row": index,
            "name": str(person.get("name") or "")[:200],
            "email": str(person.get("email") or "")[:320],
            "sessions": [str(c) for c in course_ids if isinstance(c, str) and c][:50],
        })
    return rows, errors
