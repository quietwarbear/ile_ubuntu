from fastapi import APIRouter, Depends, HTTPException, Query
from database import blog_posts_col, blog_comments_col
from middleware import get_current_user
from datetime import datetime, timezone
from typing import Optional
import uuid
import re

router = APIRouter(prefix="/api/blog", tags=["blog"])

CATEGORIES = ["Announcements", "Teaching", "Community", "Culture", "Research", "Events", "Reflections"]
FACULTY_ROLES = {"faculty", "elder", "admin"}


def slugify(text: str) -> str:
    slug = re.sub(r'[^\w\s-]', '', text.lower().strip())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:80]


def format_post(post: dict, include_content: bool = False) -> dict:
    out = {
        "id": post["id"],
        "title": post["title"],
        "slug": post["slug"],
        "excerpt": post.get("excerpt", ""),
        "cover_image": post.get("cover_image", ""),
        "author_id": post["author_id"],
        "author_name": post["author_name"],
        "author_role": post.get("author_role", ""),
        "category": post.get("category", ""),
        "tags": post.get("tags", []),
        "visibility": post.get("visibility", "public"),
        "status": post.get("status", "published"),
        "comments_count": post.get("comments_count", 0),
        "created_at": post.get("created_at", ""),
        "updated_at": post.get("updated_at", ""),
    }
    if include_content:
        out["content"] = post.get("content", "")
    return out


# ─── Public endpoints ───

@router.get("/categories")
async def get_categories():
    return CATEGORIES


@router.get("/posts/public")
async def get_public_posts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(20, le=50),
    skip: int = 0,
):
    """Public endpoint — no auth. Returns published public posts only."""
    query = {"status": "published", "visibility": "public"}
    if category:
        query["category"] = category
    if tag:
        query["tags"] = tag

    posts = list(blog_posts_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    total = blog_posts_col.count_documents(query)
    return {"posts": [format_post(p) for p in posts], "total": total}


# ─── Authenticated endpoints ───

@router.get("/posts")
async def get_posts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    visibility: Optional[str] = None,
    limit: int = Query(20, le=50),
    skip: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Auth endpoint — returns all published posts (public + members)."""
    query = {"status": "published"}
    if category:
        query["category"] = category
    if tag:
        query["tags"] = tag
    if visibility:
        query["visibility"] = visibility

    posts = list(blog_posts_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    total = blog_posts_col.count_documents(query)
    return {"posts": [format_post(p) for p in posts], "total": total}


@router.get("/posts/mine")
async def get_my_posts(current_user: dict = Depends(get_current_user)):
    """Get posts authored by the current user."""
    posts = list(blog_posts_col.find({"author_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1))
    return [format_post(p) for p in posts]


@router.get("/posts/by-slug/{slug}")
async def get_post_by_slug(slug: str, current_user: dict = Depends(get_current_user)):
    post = blog_posts_col.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["visibility"] == "members" and not current_user:
        raise HTTPException(status_code=403, detail="Members only")
    return format_post(post, include_content=True)


@router.get("/posts/public/by-slug/{slug}")
async def get_public_post_by_slug(slug: str):
    """Public endpoint — no auth. Returns a single published public post."""
    post = blog_posts_col.find_one({"slug": slug, "status": "published", "visibility": "public"}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not public")
    return format_post(post, include_content=True)


@router.post("/posts")
async def create_post(body: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in FACULTY_ROLES:
        raise HTTPException(status_code=403, detail="Only faculty, elders, and admins can publish")

    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    content = body.get("content", "")
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while blog_posts_col.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = datetime.now(timezone.utc).isoformat()
    excerpt = body.get("excerpt", "")
    if not excerpt and content:
        clean = re.sub(r'[#*_\[\]()>`~]', '', content)
        excerpt = clean[:200].strip() + ("..." if len(clean) > 200 else "")

    post = {
        "id": str(uuid.uuid4()),
        "title": title,
        "slug": slug,
        "content": content,
        "excerpt": excerpt,
        "cover_image": body.get("cover_image", ""),
        "author_id": current_user["id"],
        "author_name": current_user.get("name", current_user.get("email", "")),
        "author_role": current_user["role"],
        "category": body.get("category", ""),
        "tags": body.get("tags", []),
        "visibility": body.get("visibility", "public"),
        "status": body.get("status", "published"),
        "comments_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    blog_posts_col.insert_one(post)
    post.pop("_id", None)
    return format_post(post, include_content=True)


@router.put("/posts/{post_id}")
async def update_post(post_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    post = blog_posts_col.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for field in ["title", "content", "excerpt", "cover_image", "category", "tags", "visibility", "status"]:
        if field in body:
            updates[field] = body[field]

    if "title" in updates and updates["title"] != post["title"]:
        base_slug = slugify(updates["title"])
        slug = base_slug
        counter = 1
        while blog_posts_col.find_one({"slug": slug, "id": {"$ne": post_id}}):
            slug = f"{base_slug}-{counter}"
            counter += 1
        updates["slug"] = slug

    if "content" in updates and not body.get("excerpt"):
        clean = re.sub(r'[#*_\[\]()>`~]', '', updates["content"])
        updates["excerpt"] = clean[:200].strip() + ("..." if len(clean) > 200 else "")

    blog_posts_col.update_one({"id": post_id}, {"$set": updates})
    updated = blog_posts_col.find_one({"id": post_id}, {"_id": 0})
    return format_post(updated, include_content=True)


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    post = blog_posts_col.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    blog_posts_col.delete_one({"id": post_id})
    blog_comments_col.delete_many({"post_id": post_id})
    return {"status": "deleted"}


# ─── Comments ───

@router.get("/posts/{post_id}/comments")
async def get_comments(post_id: str, current_user: dict = Depends(get_current_user)):
    comments = list(blog_comments_col.find({"post_id": post_id}, {"_id": 0}).sort("created_at", 1))
    return comments


@router.post("/posts/{post_id}/comments")
async def add_comment(post_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    post = blog_posts_col.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment content required")

    comment = {
        "id": str(uuid.uuid4()),
        "post_id": post_id,
        "author_id": current_user["id"],
        "author_name": current_user.get("name", current_user.get("email", "")),
        "author_role": current_user.get("role", "student"),
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    blog_comments_col.insert_one(comment)
    comment.pop("_id", None)
    blog_posts_col.update_one({"id": post_id}, {"$inc": {"comments_count": 1}})
    return comment


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    comment = blog_comments_col.find_one({"id": comment_id}, {"_id": 0})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["author_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    blog_comments_col.delete_one({"id": comment_id})
    blog_posts_col.update_one({"id": comment["post_id"]}, {"$inc": {"comments_count": -1}})
    return {"status": "deleted"}
