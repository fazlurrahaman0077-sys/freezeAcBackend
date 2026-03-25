from pydantic import BaseModel


class BlogPostCreate(BaseModel):
    slug: str
    title: str
    excerpt: str = ""
    content: str = ""
    cover_image: str = ""
    published: bool = False
    tags: list[str] = []
    meta_title: str = ""
    meta_description: str = ""


class BlogPostUpdate(BaseModel):
    title: str | None = None
    excerpt: str | None = None
    content: str | None = None
    cover_image: str | None = None
    published: bool | None = None
    tags: list[str] | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class BlogPostResponse(BaseModel):
    id: str
    slug: str
    title: str
    excerpt: str
    content: str
    cover_image: str
    author_id: str | None
    published: bool
    tags: list[str]
    meta_title: str
    meta_description: str
    created_at: str
    updated_at: str
