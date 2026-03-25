from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user
from app.models.auth import (
    AuthResponse,
    LoginRequest,
    ProfileResponse,
    ProfileUpdate,
    SignUpRequest,
)
from app.services.supabase import supabase_admin, supabase_public

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignUpRequest):
    res = supabase_public.auth.sign_up(
        {
            "email": body.email,
            "password": body.password,
            "options": {"data": {"full_name": body.full_name}},
        }
    )

    if not res.user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signup failed")

    return AuthResponse(
        access_token=res.session.access_token if res.session else "",
        refresh_token=res.session.refresh_token if res.session else "",
        user_id=res.user.id,
        email=res.user.email or body.email,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    res = supabase_public.auth.sign_in_with_password(
        {"email": body.email, "password": body.password}
    )

    if not res.user or not res.session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    return AuthResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=res.user.id,
        email=res.user.email or body.email,
    )


@router.get("/me", response_model=ProfileResponse)
async def me(user: dict = Depends(get_current_user)):
    return ProfileResponse(**user)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return ProfileResponse(**user)

    res = (
        supabase_admin.table("profiles")
        .update(updates)
        .eq("id", user["id"])
        .execute()
    )

    return ProfileResponse(**res.data[0])


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"ok": True}
