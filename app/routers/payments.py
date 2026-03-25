from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, require_admin
from app.models.payment import PaymentCreate, PaymentResponse
from app.services.supabase import supabase_admin

router = APIRouter(prefix="/payments", tags=["payments"])


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
