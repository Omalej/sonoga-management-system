import uuid
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


@transaction.atomic
def check_in_reservation(reservation_id, room, user):
    """
    Check a confirmed reservation into a room.

    Creates a Stay and Folio, updates the reservation status,
    and marks the room as occupied.
    """

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related("guest", "room_type", "business_unit")
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

    if room.business_unit_id != reservation.business_unit_id:
        raise ValidationError("Room must belong to the same hotel.")

    if room.room_type_id != reservation.room_type_id:
        raise ValidationError("Room must match the reserved room type.")

    if not room.is_ready:
        raise ValidationError(
            "Room must be vacant, clean, clear of maintenance, "
            "and unblocked before check-in."
        )

    if Stay.objects.filter(reservation=reservation).exists():
        raise ValidationError("This reservation already has a stay.")

    now = timezone.now()

    stay = Stay.objects.create(
        reservation=reservation,
        guest=reservation.guest,
        room=room,
        checked_in_at=now,
        checked_in_by=user,
        status=Stay.Status.IN_HOUSE,
    )

    Folio.objects.create(stay=stay)

    reservation.assigned_room = room
    reservation.status = Reservation.Status.CHECKED_IN
    reservation.save(
        update_fields=[
            "assigned_room",
            "status",
            "updated_at",
        ]
    )

    room.occupancy_status = Room.Occupancy.OCCUPIED
    room.save(update_fields=["occupancy_status", "updated_at"])

    return stay


@transaction.atomic
def check_out_stay(reservation_id, user, allow_balance=False):
    """
    Check out the active stay for a reservation.

    Closes the folio, marks the stay checked out,
    makes the room vacant and creates a housekeeping task.
    """

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related("guest")
        .get(pk=reservation_id)
    )

    try:
        stay = (
            Stay.objects
            .select_for_update()
            .select_related("room", "folio")
            .get(reservation=reservation)
        )
    except Stay.DoesNotExist:
        raise ValidationError("This reservation has no stay.")

    if stay.status != Stay.Status.IN_HOUSE:
        raise ValidationError("This guest has already checked out.")

    folio = getattr(stay, "folio", None)

    if folio and not allow_balance and folio.balance > 0:
        raise ValidationError(
            f"Outstanding folio balance is â‚¦{folio.balance:,.2f}."
        )

    now = timezone.now()

    stay.status = Stay.Status.CHECKED_OUT
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
        folio.save(update_fields=["is_closed", "closed_at", "updated_at"])

    room = stay.room
    room.occupancy_status = Room.Occupancy.VACANT
    room.housekeeping_status = Room.Housekeeping.DIRTY
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
        notes=f"Checkout cleaning for reservation {reservation.reservation_number}.",
    )

    reservation.status = Reservation.Status.CHECKED_OUT
    reservation.save(update_fields=["status", "updated_at"])

    return stay


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
    Record a payment against the active reservation folio.
    """

    reservation = (
        Reservation.objects
        .select_related("stay")
        .get(pk=reservation_id)
    )

    try:
        folio = reservation.stay.folio
    except (Stay.DoesNotExist, Folio.DoesNotExist):
        raise ValidationError(
            "This reservation does not have an active folio."
        )

    if folio.is_closed:
        raise ValidationError("This folio is already closed.")

    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    if not reference:
        reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"

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

@transaction.atomic
def verify_housekeeping_task(task_id, user):
    """
    Verify a completed housekeeping task and return the room
    to ready/vacant status when maintenance is clear.
    """

    task = (
        HousekeepingTask.objects
        .select_for_update()
        .select_related("room")
        .get(pk=task_id)
    )

    if task.status != HousekeepingTask.Status.COMPLETED:
        raise ValidationError(
            "Only completed housekeeping tasks can be verified."
        )

    room = task.room

    task.status = HousekeepingTask.Status.VERIFIED
    task.verified_by = user
    task.save(
        update_fields=[
            "status",
            "verified_by",
            "updated_at",
        ]
    )

    room.housekeeping_status = Room.Housekeeping.CLEAN

    if room.maintenance_status == Room.Maintenance.CLEAR:
        room.occupancy_status = Room.Occupancy.VACANT

    room.save(
        update_fields=[
            "housekeeping_status",
            "occupancy_status",
            "updated_at",
        ]
    )

    return task


@transaction.atomic
def swap_guest(reservation, new_guest):
    """
    Change the guest attached to a reservation.

    If the reservation already has a Stay, the Stay guest
    is updated as well.

    The room, dates, rate, reservation number, folio and payments
    remain unchanged.
    """

    if not isinstance(reservation, Reservation):
        raise ValidationError("Invalid reservation.")

    if not isinstance(new_guest, Guest):
        raise ValidationError("Invalid guest.")

    reservation = (
        Reservation.objects
        .select_for_update()
        .select_related("guest")
        .get(pk=reservation.pk)
    )

    old_guest = reservation.guest

    if old_guest.pk == new_guest.pk:
        raise ValidationError(
            "The selected guest is already assigned to this reservation."
        )

    reservation.guest = new_guest
    reservation.save(
        update_fields=[
            "guest",
            "updated_at",
        ]
    )

    stay = Stay.objects.filter(
        reservation=reservation
    ).select_for_update().first()

    if stay:
        stay.guest = new_guest
        stay.save(
            update_fields=[
                "guest",
                "updated_at",
            ]
        )

    return reservation

