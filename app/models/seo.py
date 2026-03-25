from pydantic import BaseModel


class SeoPageCreate(BaseModel):
    slug: str
    title: str
    description: str = ""
    content: str = ""
    h1: str = ""
    canonical_url: str = ""
    og_image: str = ""
    published: bool = False


class SeoPageUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    h1: str | None = None
    canonical_url: str | None = None
    og_image: str | None = None
    published: bool | None = None


class SeoPageResponse(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    content: str
    h1: str
    canonical_url: str
    og_image: str
    published: bool
    created_at: str
    updated_at: str
