import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Reservation,
    Stay,
    Guest,
    Room,
    Folio,
    FolioCharge,
    Payment,
    HousekeepingTask,
)


# ============================================================
# CHECK-IN
# ============================================================

@transaction.atomic
def check_in_reservation(
    reservation_id,
    room,
    user,
):
    """
    Check a confirmed or pending reservation into a physical room.

    Creates:
        - Stay
        - Folio
        - Accommodation/room charge

    Updates:
        - Reservation status
        - Assigned physical room
        - Room occupancy
    """

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related(
            "guest",
            "room_type",
            "business_unit",
        )
        .get(pk=reservation_id)
    )

    if reservation.status not in (
        Reservation.Status.PENDING,
        Reservation.Status.CONFIRMED,
    ):
        raise ValidationError(
            f"Reservation cannot be checked in while it is "
            f"{reservation.get_status_display()}."
        )

    if not isinstance(room, Room):
        raise ValidationError("Invalid room.")

    room = (
        Room.objects
        .select_for_update()
        .select_related(
            "room_type",
            "business_unit",
        )
        .get(pk=room.pk)
    )

    if room.business_unit_id != reservation.business_unit_id:
        raise ValidationError(
            "Room must belong to the same hotel."
        )

    if room.room_type_id != reservation.room_type_id:
        raise ValidationError(
            "Room must match the reserved room type."
        )

    if not room.is_ready:
        raise ValidationError(
            "Room must be vacant, clean, clear of maintenance, "
            "and unblocked before check-in."
        )

    if Stay.objects.filter(
        reservation=reservation
    ).exists():
        raise ValidationError(
            "This reservation already has a stay."
        )

    now = timezone.now()

    stay = Stay.objects.create(
        reservation=reservation,
        guest=reservation.guest,
        room=room,
        checked_in_at=now,
        checked_in_by=user,
        status=Stay.Status.IN_HOUSE,
    )

    folio = Folio.objects.create(
        stay=stay
    )

    accommodation_total = (
        reservation.accommodation_total
    )

    if accommodation_total > Decimal("0.00"):
        FolioCharge.objects.create(
            folio=folio,
            charge_type=FolioCharge.ChargeType.ROOM,
            description=(
                f"Accommodation - "
                f"{reservation.room_type.name} - "
                f"{reservation.nights} night"
                f"{'s' if reservation.nights != 1 else ''} - "
                f"Room {room.number}"
            ),
            amount=accommodation_total,
            posted_by=user,
        )

    reservation.assigned_room = room
    reservation.status = Reservation.Status.CHECKED_IN

    reservation.save(
        update_fields=[
            "assigned_room",
            "status",
            "updated_at",
        ]
    )

    room.occupancy_status = (
        Room.Occupancy.OCCUPIED
    )

    room.save(
        update_fields=[
            "occupancy_status",
            "updated_at",
        ]
    )

    return stay


# ============================================================
# CHECK-OUT
# ============================================================

@transaction.atomic
def check_out_stay(
    reservation_id,
    user,
    allow_balance=False,
):
    """
    Check out the active stay for a reservation.
    """

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related(
            "guest"
        )
        .get(pk=reservation_id)
    )

    try:
        stay = (
            Stay.objects
            .select_for_update()
            .select_related(
                "room",
                "folio",
            )
            .get(
                reservation=reservation
            )
        )

    except Stay.DoesNotExist:
        raise ValidationError(
            "This reservation has no stay."
        )

    if stay.status != Stay.Status.IN_HOUSE:
        raise ValidationError(
            "This guest has already checked out."
        )

    folio = getattr(
        stay,
        "folio",
        None,
    )

    if (
        folio
        and not allow_balance
        and folio.balance > Decimal("0.00")
    ):
        raise ValidationError(
            f"Outstanding folio balance is "
            f"₦{folio.balance:,.2f}."
        )

    now = timezone.now()

    stay.status = (
        Stay.Status.CHECKED_OUT
    )
    stay.checked_out_at = now
    stay.checked_out_by = user

    stay.save(
        update_fields=[
            "status",
            "checked_out_at",
            "checked_out_by",
            "updated_at",
        ]
    )

    if folio:
        folio.is_closed = True
        folio.closed_at = now

        folio.save(
            update_fields=[
                "is_closed",
                "closed_at",
                "updated_at",
            ]
        )

    room = stay.room

    room.occupancy_status = (
        Room.Occupancy.VACANT
    )
    room.housekeeping_status = (
        Room.Housekeeping.DIRTY
    )

    room.save(
        update_fields=[
            "occupancy_status",
            "housekeeping_status",
            "updated_at",
        ]
    )

    HousekeepingTask.objects.create(
        room=room,
        task_type="Checkout Cleaning",
        status=HousekeepingTask.Status.PENDING,
        priority="Normal",
        notes=(
            "Checkout cleaning for reservation "
            f"{reservation.reservation_number}."
        ),
    )

    reservation.status = (
        Reservation.Status.CHECKED_OUT
    )

    reservation.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return stay


# ============================================================
# FOLIO PAYMENT
# ============================================================

@transaction.atomic
def post_folio_payment(
    reservation_id,
    user,
    amount,
    method,
    reference="",
    external_reference="",
    notes="",
):
    """
    Record a completed payment against the active reservation folio.
    """

    # IMPORTANT:
    # Do NOT use select_related("stay") together with
    # select_for_update() here.
    #
    # PostgreSQL rejects the generated LEFT OUTER JOIN
    # because Stay is nullable from the Reservation side.

    reservation = (
        Reservation.objects
        .select_for_update()
        .get(pk=reservation_id)
    )

    try:
        stay = (
            Stay.objects
            .select_for_update()
            .get(
                reservation=reservation
            )
        )

        folio = (
            Folio.objects
            .select_for_update()
            .get(
                stay=stay
            )
        )

    except (
        Stay.DoesNotExist,
        Folio.DoesNotExist,
    ):
        raise ValidationError(
            "This reservation does not have an active folio."
        )

    if folio.is_closed:
        raise ValidationError(
            "This folio is already closed."
        )

    if amount is None:
        raise ValidationError(
            "Payment amount is required."
        )

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    if not reference:
        reference = (
            f"PAY-{uuid.uuid4().hex[:12].upper()}"
        )

    payment = Payment(
        folio=folio,
        amount=amount,
        method=method,
        reference=reference,
        external_reference=external_reference,
        status=Payment.Status.COMPLETED,
        received_by=user,
        notes=notes,
    )

    payment.full_clean()
    payment.save()

    return payment


# ============================================================
# HOUSEKEEPING VERIFICATION
# ============================================================

@transaction.atomic
def verify_housekeeping_task(
    task_id,
    user,
):
    """
    Verify a completed housekeeping task.
    """

    task = (
        HousekeepingTask.objects
        .select_for_update()
        .select_related(
            "room"
        )
        .get(pk=task_id)
    )

    if task.status != (
        HousekeepingTask.Status.COMPLETED
    ):
        raise ValidationError(
            "Only completed housekeeping tasks "
            "can be verified."
        )

    room = task.room

    task.status = (
        HousekeepingTask.Status.VERIFIED
    )
    task.verified_by = user

    task.save(
        update_fields=[
            "status",
            "verified_by",
            "updated_at",
        ]
    )

    room.housekeeping_status = (
        Room.Housekeeping.CLEAN
    )

    if (
        room.maintenance_status
        == Room.Maintenance.CLEAR
    ):
        room.occupancy_status = (
            Room.Occupancy.VACANT
        )

    room.save(
        update_fields=[
            "housekeeping_status",
            "occupancy_status",
            "updated_at",
        ]
    )

    return task


# ============================================================
# ROOM TRANSFER
# ============================================================

@transaction.atomic
def transfer_stay_room(
    reservation,
    new_room,
    user,
):
    """
    Move an in-house guest from the current room to another room.
    """

    if not isinstance(reservation, Reservation):
        raise ValidationError(
            "Invalid reservation."
        )

    if not isinstance(new_room, Room):
        raise ValidationError(
            "Invalid room."
        )

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related(
            "guest",
            "room_type",
            "business_unit",
        )
        .get(pk=reservation.pk)
    )

    if reservation.status != Reservation.Status.CHECKED_IN:
        raise ValidationError(
            "Only a checked-in reservation can be moved "
            "to another room."
        )

    try:
        stay = (
            Stay.objects
            .select_for_update()
            .select_related(
                "room",
            )
            .get(
                reservation=reservation,
                status=Stay.Status.IN_HOUSE,
            )
        )

    except Stay.DoesNotExist:
        raise ValidationError(
            "This reservation does not have an active stay."
        )

    old_room = stay.room

    if old_room.pk == new_room.pk:
        raise ValidationError(
            "The selected room is already assigned "
            "to this guest."
        )

    room_ids = sorted([
        old_room.pk,
        new_room.pk,
    ])

    locked_rooms = list(
        Room.objects
        .select_for_update()
        .select_related(
            "room_type",
            "business_unit",
        )
        .filter(pk__in=room_ids)
        .order_by("pk")
    )

    locked_by_id = {
        room.pk: room
        for room in locked_rooms
    }

    old_room = locked_by_id[old_room.pk]
    new_room = locked_by_id[new_room.pk]

    if new_room.business_unit_id != reservation.business_unit_id:
        raise ValidationError(
            "The new room must belong to the same hotel."
        )

    if new_room.room_type_id != reservation.room_type_id:
        raise ValidationError(
            "The new room must match the reserved room type."
        )

    if not new_room.is_ready:
        raise ValidationError(
            "The new room must be vacant, clean, clear of "
            "maintenance, and unblocked."
        )

    stay.room = new_room

    stay.save(
        update_fields=[
            "room",
            "updated_at",
        ]
    )

    reservation.assigned_room = new_room

    reservation.save(
        update_fields=[
            "assigned_room",
            "updated_at",
        ]
    )

    old_room.occupancy_status = (
        Room.Occupancy.VACANT
    )

    old_room.housekeeping_status = (
        Room.Housekeeping.DIRTY
    )

    old_room.save(
        update_fields=[
            "occupancy_status",
            "housekeeping_status",
            "updated_at",
        ]
    )

    HousekeepingTask.objects.create(
        room=old_room,
        task_type="Room Transfer Cleaning",
        status=HousekeepingTask.Status.PENDING,
        priority="Normal",
        notes=(
            "Cleaning required after room transfer for "
            f"reservation {reservation.reservation_number}. "
            f"Guest moved from Room {old_room.number} "
            f"to Room {new_room.number}."
        ),
    )

    new_room.occupancy_status = (
        Room.Occupancy.OCCUPIED
    )

    new_room.save(
        update_fields=[
            "occupancy_status",
            "updated_at",
        ]
    )

    return stay