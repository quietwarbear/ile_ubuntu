"""Kindred → Ile Ubuntu handoff routes (item X2). See kindred_handoff.py.

Teacher-facing (signed in to Ile Ubuntu):
  GET    /api/kindred-handoff/key   whether a connection key is active
  POST   /api/kindred-handoff/key   issue a new key (shown once; revokes the old)
  DELETE /api/kindred-handoff/key   revoke

Server-to-server (signed by Kindred, carry the teacher's connection key):
  POST /api/kindred-handoff/courses  courses the key's teacher runs
  POST /api/kindred-handoff/import   enroll attendees: {connection_key,
       attendees: [{name, email, course_ids}], dry_run, event_ref}
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

import bulk_enrollment
import kindred_handoff
from events import emit
from middleware import get_current_user
from rate_limit import rate_limit

router = APIRouter(prefix="/api/kindred-handoff", tags=["kindred-handoff"])
logger = logging.getLogger(__name__)


def _require_course_staff(user: dict) -> None:
    if not bulk_enrollment.importable_courses(user):
        raise HTTPException(
            status_code=403,
            detail="Only someone who teaches a course can connect Kindred to it.",
        )


@router.get("/key")
def key_status(current_user: dict = Depends(get_current_user)):
    return kindred_handoff.key_status(current_user)


@router.post("/key")
def issue_key(request: Request, current_user: dict = Depends(get_current_user)):
    rate_limit(request, "kindred_handoff_key", max_requests=10, window_seconds=600)
    _require_course_staff(current_user)
    key = kindred_handoff.issue_key(current_user)
    emit("kindred_handoff.key_issued", current_user, "user", current_user["id"])
    return {"key": key, **kindred_handoff.key_status(current_user)}


@router.delete("/key")
def revoke_key(current_user: dict = Depends(get_current_user)):
    revoked = kindred_handoff.revoke_key(current_user)
    if revoked:
        emit("kindred_handoff.key_revoked", current_user, "user", current_user["id"])
    return {"active": False, "revoked": revoked}


async def _signed_body(request: Request) -> dict:
    body = await request.body()
    try:
        kindred_handoff.verify_signature(
            request.headers.get("x-handoff-timestamp"),
            request.headers.get("x-handoff-signature"),
            body,
        )
        data = json.loads(body or b"{}")
    except kindred_handoff.HandoffAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)
    except ValueError:
        raise HTTPException(status_code=400, detail="Send JSON.")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Send JSON.")
    return data


def _teacher(data: dict) -> dict:
    try:
        return kindred_handoff.resolve_key(data.get("connection_key"))
    except kindred_handoff.HandoffAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)


@router.post("/courses")
async def handoff_courses(request: Request):
    rate_limit(request, "kindred_handoff_courses", max_requests=120, window_seconds=600)
    data = await _signed_body(request)
    teacher = _teacher(data)
    return {
        "teacher_name": teacher.get("name", ""),
        "courses": bulk_enrollment.importable_courses(teacher),
    }


@router.post("/import")
async def handoff_import(request: Request):
    rate_limit(request, "kindred_handoff_import", max_requests=60, window_seconds=600)
    data = await _signed_body(request)
    teacher = _teacher(data)
    try:
        rows, row_errors = kindred_handoff.rows_from_attendees(data.get("attendees"))
    except kindred_handoff.HandoffAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)
    dry_run = bool(data.get("dry_run"))
    # actor = the teacher, so the import only reaches courses they run.
    report = bulk_enrollment.import_enrollments(rows, {}, teacher, dry_run=dry_run)
    report["errors"] = sorted(row_errors + report["errors"], key=lambda e: e["row"])
    report["counts"]["errors"] = len(report["errors"])
    event_ref = str(data.get("event_ref") or "")[:100]
    if not dry_run:
        emit("kindred_handoff.imported", teacher, "user", teacher["id"],
             meta={"event_ref": event_ref, **report["counts"]})
    # Counts only: no names or emails in the log.
    logger.info("kindred handoff dry_run=%s event_ref=%s counts=%s", dry_run, event_ref, report["counts"])
    return report
