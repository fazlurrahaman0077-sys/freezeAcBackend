from typing import Any

from pydantic import BaseModel


class ServiceItem(BaseModel):
    serviceId: str
    qty: int
    title: str = ""
    price: float = 0.0


class BookingCreate(BaseModel):
    """Authenticated booking creation (kept for backward-compat)."""
    service: str
    amount: float
    scheduled_at: str | None = None
    address: str = ""
    building: str = ""
    name: str = ""
    phone: str = ""
    notes: str = ""


class BookingPublicCreate(BaseModel):
    """Anonymous booking from the UI — no JWT required."""
    services: list[ServiceItem]
    address: str
    building: str
    scheduled_at: str | None = None   # ISO datetime or "Thu Mar 27 at 9:00 AM"
    name: str = ""
    phone: str = ""
    amount: float
    notes: str = ""


class BookingUpdate(BaseModel):
    status: str | None = None
    scheduled_at: str | None = None
    address: str | None = None
    building: str | None = None
    name: str | None = None
    phone: str | None = None
    notes: str | None = None


class BookingResponse(BaseModel):
    id: str
    user_id: str | None
    service: str
    services: list[Any] = []
    amount: float
    status: str
    scheduled_at: str | None
    address: str
    building: str = ""
    name: str = ""
    phone: str = ""
    notes: str
    created_at: str
    updated_at: str
