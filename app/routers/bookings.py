from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, require_admin
from app.models.booking import BookingCreate, BookingResponse, BookingUpdate
from app.services.supabase import supabase_admin

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingCreate,
    user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    data["user_id"] = user["id"]

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
