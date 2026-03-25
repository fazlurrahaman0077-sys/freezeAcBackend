from pydantic import BaseModel


class BookingCreate(BaseModel):
    service: str
    amount: float
    scheduled_at: str | None = None
    address: str = ""
    notes: str = ""


class BookingUpdate(BaseModel):
    status: str | None = None
    scheduled_at: str | None = None
    address: str | None = None
    notes: str | None = None


class BookingResponse(BaseModel):
    id: str
    user_id: str
    service: str
    amount: float
    status: str
    scheduled_at: str | None
    address: str
    notes: str
    created_at: str
    updated_at: str
