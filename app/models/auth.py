from pydantic import BaseModel, EmailStr
from typing import Literal


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPSendRequest(BaseModel):
    """Send OTP to phone (SMS) or email (magic-link/OTP)."""
    phone: str | None = None   # E.164 format: +971585793050
    email: EmailStr | None = None

    def mode(self) -> Literal["phone", "email"]:
        if self.phone:
            return "phone"
        if self.email:
            return "email"
        raise ValueError("Provide either phone or email")


class OTPVerifyRequest(BaseModel):
    """Verify the 6-digit OTP received by SMS or email."""
    phone: str | None = None
    email: EmailStr | None = None
    token: str                    # 6-digit OTP
    type: Literal["sms", "email"] = "sms"


class OTPSendResponse(BaseModel):
    message: str
    mode: str   # "phone" | "email"


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    phone: str = ""


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    phone: str
    role: str
    avatar_url: str
    created_at: str
