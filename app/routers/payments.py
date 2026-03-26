import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.deps import get_current_user, require_admin
from app.models.payment import PaymentCreate, PaymentResponse, ZiinaWebhookEvent
from app.services.supabase import supabase_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


# ---------------------------------------------------------------------------
# Ziina payment-link helper
# ---------------------------------------------------------------------------

PAY_BASE = "https://pay.ziina.com"


def ziina_pay_link(amount_aed: float, reference: str = "") -> str:
    """
    Build a Ziina payment link.
    The UI applies the fee-reversal formula so the customer pays the exact AED
    amount shown on screen.  We replicate that here for server-generated links.
    adjusted = (amount - 1.05) / 1.030452
    """
    adjusted = round((amount_aed - 1.05) / 1.030452, 2)
    url = f"{PAY_BASE}/{settings.ziina_merchant_id}?amount={adjusted}"
    if reference:
        url += f"&reference={reference}"
    return url


# ---------------------------------------------------------------------------
# Ziina webhook
# ---------------------------------------------------------------------------

@router.post("/ziina/webhook", status_code=status.HTTP_200_OK)
async def ziina_webhook(request: Request):
    """
    Receives Ziina payment notifications.
    Ziina POSTs JSON when a payment succeeds or fails.
    Optional HMAC-SHA256 signature verification via X-Ziina-Signature header.
    """
    raw_body = await request.body()

    # Verify signature if webhook secret is configured
    if settings.ziina_webhook_secret:
        sig_header = request.headers.get("X-Ziina-Signature", "")
        expected = hmac.new(
            settings.ziina_webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature")

    try:
        payload = ZiinaWebhookEvent.model_validate_json(raw_body)
    except Exception as exc:
        logger.warning("Ziina webhook parse error: %s", exc)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid payload")

    # Normalise status: Ziina uses "SUCCESS" / "FAILED"
    event_status = (payload.status or "").upper()
    payment_intent_id = payload.payment_intent_id or payload.id or ""
    reference = payload.reference or ""  # we pass booking_id as reference

    if event_status == "SUCCESS":
        new_payment_status = "completed"
        new_booking_status = "confirmed"
    elif event_status == "FAILED":
        new_payment_status = "failed"
        new_booking_status = None  # keep booking as-is on failure
    else:
        # PENDING or unknown — do nothing
        return {"received": True}

    # Update payment record by provider_ref or booking_id
    payment_query = supabase_admin.table("payments")

    if payment_intent_id:
        payment_res = (
            payment_query
            .update({"status": new_payment_status, "provider_ref": payment_intent_id})
            .eq("provider_ref", payment_intent_id)
            .execute()
        )
        if not payment_res.data and reference:
            # Fallback: match by booking_id stored as reference
            payment_query.update(
                {"status": new_payment_status, "provider_ref": payment_intent_id}
            ).eq("booking_id", reference).execute()
    elif reference:
        payment_query.update(
            {"status": new_payment_status, "provider_ref": payment_intent_id}
        ).eq("booking_id", reference).execute()

    # Update the linked booking status
    if new_booking_status and reference:
        supabase_admin.table("bookings").update(
            {"status": new_booking_status}
        ).eq("id", reference).execute()

    logger.info(
        "Ziina webhook processed: intent=%s status=%s reference=%s",
        payment_intent_id,
        event_status,
        reference,
    )
    return {"received": True}


# ---------------------------------------------------------------------------
# Standard CRUD endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    data["user_id"] = user["id"]

    res = supabase_admin.table("payments").insert(data).execute()

    if not res.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create payment")

    return PaymentResponse(**res.data[0])


@router.get("/", response_model=list[PaymentResponse])
async def list_payments(user: dict = Depends(get_current_user)):
    res = (
        supabase_admin.table("payments")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return [PaymentResponse(**p) for p in res.data]


@router.get("/all", response_model=list[PaymentResponse])
async def list_all_payments(admin: dict = Depends(require_admin)):
    res = (
        supabase_admin.table("payments")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [PaymentResponse(**p) for p in res.data]


@router.patch("/{payment_id}/complete", response_model=PaymentResponse)
async def complete_payment(
    payment_id: str,
    provider_ref: str = "",
    admin: dict = Depends(require_admin),
):
    res = (
        supabase_admin.table("payments")
        .update({"status": "completed", "provider_ref": provider_ref})
        .eq("id", payment_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    return PaymentResponse(**res.data[0])
