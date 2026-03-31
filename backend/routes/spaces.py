from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import spaces_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/spaces", tags=["spaces"])

ACCESS_LEVELS = ["public", "members", "faculty", "elder"]


@router.post("")
async def create_space(request: Request, current_user: dict = Depends(get_current_user)):
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can create spaces")

    data = await request.json()
    space = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "description": data.get("description", ""),
        "access_level": data.get("access_level", "members"),
        "content": data.get("content", ""),
        "resources": [],
        "owner_id": current_user["id"],
        "owner_name": current_user["name"],
        "members": [current_user["id"]],
        "pending_requests": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    spaces_col.insert_one(space)
    space.pop("_id", None)
    return space


@router.get("")
async def list_spaces(current_user: dict = Depends(get_current_user)):
    all_spaces = list(spaces_col.find({}, {"_id": 0}).sort("created_at", -1))
    visible = []
    for s in all_spaces:
        if s["access_level"] == "public":
            visible.append(s)
        elif s["access_level"] == "members" and current_user["id"] in s.get("members", []):
            visible.append(s)
        elif s["access_level"] == "faculty" and has_permission(current_user["role"], UserRole.FACULTY):
            visible.append(s)
        elif s["access_level"] == "elder" and has_permission(current_user["role"], UserRole.ELDER):
            visible.append(s)
        elif s["owner_id"] == current_user["id"]:
            visible.append(s)
    return visible


@router.get("/{space_id}")
async def get_space(space_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id}, {"_id": 0})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Check access
    if not _can_access(space, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this space")

    return space


@router.put("/{space_id}")
async def update_space(space_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    data = await request.json()
    update_fields = {}
    for field in ["name", "description", "access_level", "content"]:
        if field in data:
            update_fields[field] = data[field]
    update_fields["updated_at"] = datetime.now(timezone.utc)

    spaces_col.update_one({"id": space_id}, {"$set": update_fields})
    updated = spaces_col.find_one({"id": space_id}, {"_id": 0})
    return updated


@router.delete("/{space_id}")
async def delete_space(space_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    spaces_col.delete_one({"id": space_id})
    return {"success": True}


@router.post("/{space_id}/request-access")
async def request_access(space_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if current_user["id"] in space.get("members", []):
        raise HTTPException(status_code=400, detail="Already a member")

    if current_user["id"] in [r["user_id"] for r in space.get("pending_requests", [])]:
        raise HTTPException(status_code=400, detail="Request already pending")

    req = {
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    spaces_col.update_one({"id": space_id}, {"$push": {"pending_requests": req}})
    return {"success": True, "message": "Access requested"}


@router.post("/{space_id}/approve/{user_id}")
async def approve_access(space_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owner can approve")

    spaces_col.update_one(
        {"id": space_id},
        {
            "$addToSet": {"members": user_id},
            "$pull": {"pending_requests": {"user_id": user_id}},
        },
    )
    return {"success": True}


@router.post("/{space_id}/deny/{user_id}")
async def deny_access(space_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owner can deny")

    spaces_col.update_one(
        {"id": space_id},
        {"$pull": {"pending_requests": {"user_id": user_id}}},
    )
    return {"success": True}


@router.post("/{space_id}/invite")
async def invite_member(space_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owner can invite")

    data = await request.json()
    user_id = data.get("user_id")
    spaces_col.update_one({"id": space_id}, {"$addToSet": {"members": user_id}})
    return {"success": True}


@router.post("/{space_id}/remove/{user_id}")
async def remove_member(space_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if space["owner_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owner can remove members")

    spaces_col.update_one({"id": space_id}, {"$pull": {"members": user_id}})
    return {"success": True}


@router.post("/{space_id}/resources")
async def add_resource(space_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    space = spaces_col.find_one({"id": space_id})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if not _can_access(space, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    if not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Only faculty+ can add resources")

    data = await request.json()
    resource = {
        "id": str(uuid.uuid4()),
        "title": data["title"],
        "type": data.get("type", "text"),
        "content": data.get("content", ""),
        "url": data.get("url", ""),
        "added_by": current_user["id"],
        "added_by_name": current_user["name"],
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    spaces_col.update_one({"id": space_id}, {"$push": {"resources": resource}})
    return resource


def _can_access(space: dict, user: dict) -> bool:
    if space["owner_id"] == user["id"]:
        return True
    if space["access_level"] == "public":
        return True
    if space["access_level"] == "members" and user["id"] in space.get("members", []):
        return True
    if space["access_level"] == "faculty" and has_permission(user["role"], UserRole.FACULTY):
        return True
    if space["access_level"] == "elder" and has_permission(user["role"], UserRole.ELDER):
        return True
    return False
