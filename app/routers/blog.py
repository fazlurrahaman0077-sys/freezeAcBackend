from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, require_admin
from app.models.blog import BlogPostCreate, BlogPostResponse, BlogPostUpdate
from app.services.supabase import supabase_admin

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("/", response_model=list[BlogPostResponse])
async def list_posts(published_only: bool = True):
    query = supabase_admin.table("blog_posts").select("*")

    if published_only:
        query = query.eq("published", True)

    res = query.order("created_at", desc=True).execute()
    return [BlogPostResponse(**p) for p in res.data]


@router.get("/{slug}", response_model=BlogPostResponse)
async def get_post(slug: str):
    res = (
        supabase_admin.table("blog_posts")
        .select("*")
        .eq("slug", slug)
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    if not res.data["published"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    return BlogPostResponse(**res.data)


@router.post("/", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: BlogPostCreate,
    admin: dict = Depends(require_admin),
):
    data = body.model_dump()
    data["author_id"] = admin["id"]

    res = supabase_admin.table("blog_posts").insert(data).execute()

    if not res.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create post")

    return BlogPostResponse(**res.data[0])


@router.patch("/{post_id}", response_model=BlogPostResponse)
async def update_post(
    post_id: str,
    body: BlogPostUpdate,
    admin: dict = Depends(require_admin),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    res = (
        supabase_admin.table("blog_posts")
        .update(updates)
        .eq("id", post_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    return BlogPostResponse(**res.data[0])


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    admin: dict = Depends(require_admin),
):
    supabase_admin.table("blog_posts").delete().eq("id", post_id).execute()


@router.get("/admin/all", response_model=list[BlogPostResponse])
async def admin_list_posts(admin: dict = Depends(require_admin)):
    res = (
        supabase_admin.table("blog_posts")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [BlogPostResponse(**p) for p in res.data]
