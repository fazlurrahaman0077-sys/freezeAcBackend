from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, blog, bookings, payments, seo

app = FastAPI(title="FreezeAC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "https://freezeac.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bookings.router)
app.include_router(blog.router)
app.include_router(payments.router)
app.include_router(seo.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
