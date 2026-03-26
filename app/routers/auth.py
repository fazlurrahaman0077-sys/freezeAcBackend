import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user
from app.models.auth import (
    AuthResponse,
    LoginRequest,
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    ProfileResponse,
    ProfileUpdate,
    SignUpRequest,
)
from app.services.supabase import supabase_admin, supabase_public

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Email / Password (kept for admin use)
# ---------------------------------------------------------------------------

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
        phone=res.user.phone or "",
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
        phone=res.user.phone or "",
    )


# ---------------------------------------------------------------------------
# OTP — Phone (SMS) or Email
# ---------------------------------------------------------------------------

@router.post("/otp/send", response_model=OTPSendResponse)
async def otp_send(body: OTPSendRequest):
    """
    Send a 6-digit OTP.
    - Phone  → SMS via Supabase (needs Twilio / other SMS provider in Supabase dashboard)
    - Email  → email OTP (works out-of-the-box, no extra config)
    Creates the user automatically if they don't exist.
    """
    try:
        mode = body.mode()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        if mode == "phone":
            supabase_public.auth.sign_in_with_otp({"phone": body.phone})
        else:
            supabase_public.auth.sign_in_with_otp(
                {
                    "email": str(body.email),
                    "options": {"should_create_user": True},
                }
            )
    except Exception as exc:
        logger.error("OTP send error (%s): %s", mode, exc)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Failed to send OTP to {mode}. "
            "Check that the Supabase SMS provider is configured for phone OTP.",
        )

    return OTPSendResponse(
        message=f"OTP sent to your {mode}",
        mode=mode,
    )


@router.post("/otp/verify", response_model=AuthResponse)
async def otp_verify(body: OTPVerifyRequest):
    """
    Verify the 6-digit OTP and return JWT tokens.
    type = "sms"   for phone OTP
    type = "email" for email OTP
    """
    if not body.phone and not body.email:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide either phone or email",
        )

    params: dict = {"token": body.token, "type": body.type}
    if body.phone:
        params["phone"] = body.phone
    else:
        params["email"] = str(body.email)

    try:
        res = supabase_public.auth.verify_otp(params)
    except Exception as exc:
        logger.error("OTP verify error: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP verification failed")

    if not res.user or not res.session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired OTP")

    # Ensure a profile row exists (the trigger handles new users,
    # but phone-only users may need a manual upsert on first login)
    _ensure_profile(res.user.id, res.user.phone or "", res.user.email or "")

    return AuthResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=res.user.id,
        email=res.user.email or "",
        phone=res.user.phone or "",
    )


def _ensure_profile(user_id: str, phone: str, email: str) -> None:
    """Upsert a profile row — safe to call multiple times."""
    existing = (
        supabase_admin.table("profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        supabase_admin.table("profiles").insert(
            {"id": user_id, "phone": phone, "full_name": ""}
        ).execute()
    elif phone and not existing.data.get("phone"):
        supabase_admin.table("profiles").update({"phone": phone}).eq("id", user_id).execute()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Link anonymous bookings to a verified user (post-OTP)
# ---------------------------------------------------------------------------

@router.post("/link-bookings")
async def link_bookings(user: dict = Depends(get_current_user)):
    """
    After a user verifies their OTP, call this endpoint to claim any
    anonymous bookings that match their phone number.
    Returns the number of bookings linked.
    """
    phone = user.get("phone", "").strip()
    if not phone:
        return {"linked": 0, "message": "No phone number on profile"}

    res = (
        supabase_admin.table("bookings")
        .update({"user_id": user["id"]})
        .eq("phone", phone)
        .is_("user_id", "null")
        .execute()
    )

    linked = len(res.data) if res.data else 0
    return {"linked": linked, "message": f"Linked {linked} booking(s) to your account"}
