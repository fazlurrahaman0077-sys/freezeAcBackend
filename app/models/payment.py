from pydantic import BaseModel


class PaymentCreate(BaseModel):
    booking_id: str | None = None
    amount: float
    currency: str = "AED"
    provider: str = "ziina"
    provider_ref: str = ""


class PaymentResponse(BaseModel):
    id: str
    user_id: str
    booking_id: str | None
    amount: float
    currency: str
    provider: str
    provider_ref: str
    status: str
    created_at: str
