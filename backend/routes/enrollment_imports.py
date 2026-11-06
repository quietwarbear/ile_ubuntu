"""Roster import (item I1): upload a CSV, preview it with the session →
course mapping, confirm, get a report. The work is in bulk_enrollment.py;
this file is only the HTTP surface.

POST bodies are JSON: {"csv": "<file text>", "session_map": {label: course_id}}.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

import bulk_enrollment
from middleware import get_current_user
from rate_limit import rate_limit

router = APIRouter(prefix="/api/enrollment-imports", tags=["enrollment-imports"])

PREVIEW_ROWS = 10


async def _read(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Send the file as JSON: {csv, session_map}")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Send the file as JSON: {csv, session_map}")
    session_map = data.get("session_map") or {}
    if not isinstance(session_map, dict):
        raise HTTPException(status_code=400, detail="session_map must map each session to a course id")
    text = data.get("csv")
    if not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Attach a CSV file")
    try:
        parsed = bulk_enrollment.parse_roster_csv(text)
    except bulk_enrollment.BulkImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return parsed, {str(k): v for k, v in session_map.items() if isinstance(v, str) and v}


def _merge_errors(report: dict, parse_errors: list) -> dict:
    report["errors"] = sorted(parse_errors + report["errors"], key=lambda e: e["row"])
    report["counts"]["errors"] = len(report["errors"])
    return report


@router.get("/courses")
def importable_courses(current_user: dict = Depends(get_current_user)):
    """Courses this person can import into: ones they own or co-teach
    (every course, for a platform admin)."""
    return bulk_enrollment.importable_courses(current_user)


@router.post("/preview")
async def preview_import(request: Request, current_user: dict = Depends(get_current_user)):
    """Read the file and show what an import would do. Writes nothing."""
    rate_limit(request, "enrollment_import_preview", max_requests=60, window_seconds=600)
    parsed, session_map = await _read(request)
    labels = bulk_enrollment.session_labels(parsed["rows"])
    mapping = bulk_enrollment.suggest_mapping(labels, current_user)
    mapping.update({k: v for k, v in session_map.items() if k in mapping})
    report = bulk_enrollment.import_enrollments(
        parsed["rows"], mapping, current_user, dry_run=True
    )
    return {
        "total_rows": len(parsed["rows"]) + len(parsed["errors"]),
        "preview_rows": parsed["rows"][:PREVIEW_ROWS],
        "sessions": [{"label": label, "course_id": mapping.get(label)} for label in labels],
        "report": _merge_errors(report, parsed["errors"]),
    }


@router.post("")
async def run_import(request: Request, current_user: dict = Depends(get_current_user)):
    """Create invited accounts and enroll everyone. Safe to run again."""
    rate_limit(request, "enrollment_import", max_requests=20, window_seconds=600)
    parsed, session_map = await _read(request)
    report = bulk_enrollment.import_enrollments(parsed["rows"], session_map, current_user)
    return _merge_errors(report, parsed["errors"])
