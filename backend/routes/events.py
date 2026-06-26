"""Read access to the activity event stream. Faculty+ only.

Verification/ops surface for now; the Community Dashboard and Ubuntu
Intelligence layers will build richer aggregations on the same collection.
"""

from fastapi import APIRouter, Depends, Query
from database import events_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from fastapi import HTTPException

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def list_events(
    type: str = None,
    user_id: str = None,
    entity_type: str = None,
    entity_id: str = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List recent activity events, newest first. Faculty+ only."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Faculty access required")

    query = {}
    if type:
        query["type"] = type
    if user_id:
        query["user_id"] = user_id
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id

    events = list(
        events_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    )
    return {"events": events, "count": len(events)}


@router.get("/summary")
def events_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Event counts by type over the last N days (aggregation pipeline, indexed)."""
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Faculty access required")

    from datetime import datetime, timezone, timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = list(events_col.aggregate(pipeline))
    return {
        "days": days,
        "by_type": {r["_id"]: r["count"] for r in rows},
        "total": sum(r["count"] for r in rows),
    }
