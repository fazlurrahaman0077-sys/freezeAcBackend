from pydantic import BaseModel


class PaymentCreate(BaseModel):
    booking_id: str | None = None
    amount: float
    currency: str = "AED"
    provider: str = "ziina"
    provider_ref: str = ""


class PaymentResponse(BaseModel):
    id: str
    user_id: str | None
    booking_id: str | None
    amount: float
    currency: str
    provider: str
    provider_ref: str
    status: str
    created_at: str


class ZiinaWebhookEvent(BaseModel):
    """
    Ziina sends a POST to our webhook URL when a payment completes.
    Fields may vary — we handle the common ones flexibly.
    """
    id: str | None = None                  # payment intent id
    payment_intent_id: str | None = None   # alternate field name
    status: str = ""                       # "SUCCESS" | "FAILED" | "PENDING"
    amount: float | None = None            # amount (fils / smallest unit)
    currency: str | None = None
    reference: str | None = None           # our booking_id or payment_id
    event: str | None = None               # "payment.success" etc.
