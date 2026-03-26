from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, require_admin
from app.models.booking import (
    BookingCreate,
    BookingPublicCreate,
    BookingResponse,
    BookingUpdate,
)
from app.services.supabase import supabase_admin

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/public", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_public_booking(body: BookingPublicCreate):
    """
    Anonymous booking from the UI — no JWT required.
    Creates a booking + a pending Ziina payment record.
    """
    # Derive a single 'service' label from the cart for backward-compat columns
    service_labels = [s.title or s.serviceId for s in body.services]
    service_str = ", ".join(service_labels) if service_labels else "AC Service"

    booking_data = {
        "user_id": None,
        "service": service_str,
        "services": [s.model_dump() for s in body.services],
        "amount": body.amount,
        "status": "pending",
        "scheduled_at": body.scheduled_at,
        "address": body.address,
        "building": body.building,
        "name": body.name,
        "phone": body.phone,
        "notes": body.notes,
    }

    res = supabase_admin.table("bookings").insert(booking_data).execute()

    if not res.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create booking")

    booking = res.data[0]

    # Create a pending payment record linked to this booking
    payment_data = {
        "user_id": None,
        "booking_id": booking["id"],
        "amount": body.amount,
        "currency": "AED",
        "provider": "ziina",
        "provider_ref": "",
        "status": "pending",
    }
    supabase_admin.table("payments").insert(payment_data).execute()

    return BookingResponse(**booking)


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingCreate,
    user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    data["user_id"] = user["id"]
    data.setdefault("services", [])

    res = supabase_admin.table("bookings").insert(data).execute()

    if not res.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to create booking")

    return BookingResponse(**res.data[0])


@router.get("/", response_model=list[BookingResponse])
async def list_bookings(user: dict = Depends(get_current_user)):
    res = (
        supabase_admin.table("bookings")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return [BookingResponse(**b) for b in res.data]


@router.get("/all", response_model=list[BookingResponse])
async def list_all_bookings(admin: dict = Depends(require_admin)):
    res = (
        supabase_admin.table("bookings")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [BookingResponse(**b) for b in res.data]


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    user: dict = Depends(get_current_user),
):
    res = (
        supabase_admin.table("bookings")
        .select("*")
        .eq("id", booking_id)
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if res.data["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    return BookingResponse(**res.data)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: str,
    body: BookingUpdate,
    user: dict = Depends(get_current_user),
):
    existing = (
        supabase_admin.table("bookings")
        .select("*")
        .eq("id", booking_id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    if existing.data["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return BookingResponse(**existing.data)

    res = (
        supabase_admin.table("bookings")
        .update(updates)
        .eq("id", booking_id)
        .execute()
    )

    return BookingResponse(**res.data[0])
