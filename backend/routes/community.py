from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import posts_col
from middleware import get_current_user

router = APIRouter(prefix="/api/community", tags=["community"])


@router.post("/posts")
async def create_post(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    post = {
        "id": str(uuid.uuid4()),
        "title": data["title"],
        "content": data["content"],
        "category": data.get("category", "general"),
        "author_id": current_user["id"],
        "author_name": current_user["name"],
        "author_picture": current_user.get("picture", ""),
        "author_role": current_user["role"],
        "replies": [],
        "likes": [],
        "pinned": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    posts_col.insert_one(post)
    post.pop("_id", None)
    return post


@router.get("/posts")
async def list_posts(category: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if category:
        query["category"] = category
    posts = list(posts_col.find(query, {"_id": 0}).sort("created_at", -1))
    return posts


@router.get("/posts/{post_id}")
async def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
    post = posts_col.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{post_id}/reply")
async def reply_to_post(post_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    reply = {
        "id": str(uuid.uuid4()),
        "content": data["content"],
        "author_id": current_user["id"],
        "author_name": current_user["name"],
        "author_picture": current_user.get("picture", ""),
        "author_role": current_user["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = posts_col.update_one(
        {"id": post_id},
        {"$push": {"replies": reply}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return reply


@router.post("/posts/{post_id}/like")
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    post = posts_col.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user["id"] in post.get("likes", []):
        posts_col.update_one({"id": post_id}, {"$pull": {"likes": current_user["id"]}})
        return {"liked": False}
    else:
        posts_col.update_one({"id": post_id}, {"$addToSet": {"likes": current_user["id"]}})
        return {"liked": True}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    from models.user import has_permission, UserRole

    post = posts_col.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Access denied")

    posts_col.delete_one({"id": post_id})
    return {"success": True}
