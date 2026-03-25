from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.deps import require_admin
from app.models.seo import SeoPageCreate, SeoPageResponse, SeoPageUpdate
from app.services.supabase import supabase_admin

router = APIRouter(prefix="/seo", tags=["seo"])


@router.get("/pages", response_model=list[SeoPageResponse])
async def list_pages(published_only: bool = True):
    query = supabase_admin.table("seo_pages").select("*")

    if published_only:
        query = query.eq("published", True)

    res = query.order("created_at", desc=True).execute()
    return [SeoPageResponse(**p) for p in res.data]


@router.get("/pages/{slug}", response_model=SeoPageResponse)
async def get_page(slug: str):
    res = (
        supabase_admin.table("seo_pages")
        .select("*")
        .eq("slug", slug)
        .eq("published", True)
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")

    return SeoPageResponse(**res.data)


@router.post("/pages", response_model=SeoPageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    body: SeoPageCreate,
    admin: dict = Depends(require_admin),
):
    res = supabase_admin.table("seo_pages").insert(body.model_dump()).execute()

    if not res.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create page")

    return SeoPageResponse(**res.data[0])


@router.patch("/pages/{page_id}", response_model=SeoPageResponse)
async def update_page(
    page_id: str,
    body: SeoPageUpdate,
    admin: dict = Depends(require_admin),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    res = (
        supabase_admin.table("seo_pages")
        .update(updates)
        .eq("id", page_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")

    return SeoPageResponse(**res.data[0])


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: str,
    admin: dict = Depends(require_admin),
):
    supabase_admin.table("seo_pages").delete().eq("id", page_id).execute()


@router.get("/sitemap.xml")
async def sitemap():
    posts = (
        supabase_admin.table("blog_posts")
        .select("slug,updated_at")
        .eq("published", True)
        .execute()
    )
    pages = (
        supabase_admin.table("seo_pages")
        .select("slug,updated_at")
        .eq("published", True)
        .execute()
    )

    base = "https://freezeac.com"
    urls = [f"  <url><loc>{base}/</loc></url>"]

    for p in posts.data:
        urls.append(
            f"  <url><loc>{base}/blog/{p['slug']}</loc>"
            f"<lastmod>{p['updated_at'][:10]}</lastmod></url>"
        )

    for p in pages.data:
        urls.append(
            f"  <url><loc>{base}/{p['slug']}</loc>"
            f"<lastmod>{p['updated_at'][:10]}</lastmod></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )

    return Response(content=xml, media_type="application/xml")
