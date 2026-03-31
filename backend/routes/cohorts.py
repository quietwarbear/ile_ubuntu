from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import cohorts_col, courses_col
from middleware import get_current_user
from models.user import has_permission, UserRole
from models.cohort import CohortStatus

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


@router.post("")
async def create_cohort(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create cohorts")

    data = await request.json()
    cohort = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "description": data.get("description", ""),
        "course_id": data.get("course_id"),
        "instructor_id": current_user["id"],
        "instructor_name": current_user["name"],
        "status": CohortStatus.UPCOMING,
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "members": [],
        "max_members": data.get("max_members", 30),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    cohorts_col.insert_one(cohort)
    cohort.pop("_id", None)
    return cohort


@router.get("")
async def list_cohorts(status: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    cohorts = list(cohorts_col.find(query, {"_id": 0}).sort("created_at", -1))
    return cohorts


@router.get("/{cohort_id}")
async def get_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id}, {"_id": 0})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return cohort


@router.put("/{cohort_id}")
async def update_cohort(cohort_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if cohort["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    data = await request.json()
    update_fields = {}
    for field in ["name", "description", "status", "start_date", "end_date", "max_members"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    cohorts_col.update_one({"id": cohort_id}, {"$set": update_fields})
    updated = cohorts_col.find_one({"id": cohort_id}, {"_id": 0})
    return updated


@router.post("/{cohort_id}/join")
async def join_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    if current_user["id"] in cohort.get("members", []):
        raise HTTPException(status_code=400, detail="Already a member")

    if len(cohort.get("members", [])) >= cohort.get("max_members", 30):
        raise HTTPException(status_code=400, detail="Cohort is full")

    cohorts_col.update_one(
        {"id": cohort_id},
        {"$addToSet": {"members": current_user["id"]}},
    )
    return {"success": True, "message": "Joined cohort"}


@router.post("/{cohort_id}/leave")
async def leave_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohorts_col.update_one(
        {"id": cohort_id},
        {"$pull": {"members": current_user["id"]}},
    )
    return {"success": True, "message": "Left cohort"}


@router.delete("/{cohort_id}")
async def delete_cohort(cohort_id: str, current_user: dict = Depends(get_current_user)):
    cohort = cohorts_col.find_one({"id": cohort_id})
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if cohort["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    cohorts_col.delete_one({"id": cohort_id})
    return {"success": True}
