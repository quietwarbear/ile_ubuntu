from fastapi import APIRouter, HTTPException, Query, Request, Depends
from datetime import datetime, timezone
import os
import uuid
import httpx
from database import posts_col
from middleware import get_current_user
from events import emit

router = APIRouter(prefix="/api/community", tags=["community"])

KINDRED_API_URL = os.environ.get("KINDRED_API_URL", "https://kindred-production-badd.up.railway.app/api").rstrip("/")
KINDRED_WEB_URL = os.environ.get("KINDRED_WEB_URL", "https://www.heykindred.org").rstrip("/")


@router.post("/open-kindred")
async def open_kindred(current_user: dict = Depends(get_current_user)):
    """Start an 'Open in Kindred' jump from the community section.

    Mints a single-use code at Kindred (server-to-server, shared UBUNTU_SSO_SECRET) and
    returns the jump URL. Only a one-time code rides in the URL — never a session token.
    """
    secret = os.environ.get("UBUNTU_SSO_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Cross-product sign-in isn't configured.")
    email = (current_user.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Your account has no email to carry over.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{KINDRED_API_URL}/auth/sso-code",
                json={"email": email, "secret": secret, "name": current_user.get("name", "")},
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't reach Kindred ({exc}).")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Kindred declined the handoff (HTTP {resp.status_code}).")
    code = resp.json().get("code")
    if not code:
        raise HTTPException(status_code=502, detail="Kindred returned no code.")
    return {"url": f"{KINDRED_WEB_URL}/sso?code={code}"}


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
    emit("post.created", current_user, "post", post["id"], meta={"category": post["category"]})
    return post


@router.get("/posts")
def list_posts(
    category: str = None,
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if category:
        query["category"] = category
    posts = list(
        posts_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    )
    return posts


@router.get("/posts/{post_id}")
def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
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
    emit("post.replied", current_user, "post", post_id)
    return reply


@router.post("/posts/{post_id}/like")
def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    post = posts_col.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user["id"] in post.get("likes", []):
        posts_col.update_one({"id": post_id}, {"$pull": {"likes": current_user["id"]}})
        return {"liked": False}
    else:
        posts_col.update_one({"id": post_id}, {"$addToSet": {"likes": current_user["id"]}})
        emit("post.liked", current_user, "post", post_id)
        return {"liked": True}


@router.delete("/posts/{post_id}")
def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    from models.user import has_permission, UserRole

    post = posts_col.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Access denied")

    posts_col.delete_one({"id": post_id})
    return {"success": True}
