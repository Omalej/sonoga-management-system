import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from control.services import log_event
from .models import Folio, FolioCharge, HousekeepingTask, Payment, Reservation, Room, Stay


@transaction.atomic
def check_in_reservation(*, reservation_id: int, room: Room, user) -> Stay:
    reservation = Reservation.objects.select_for_update().select_related("guest", "room_type", "business_unit").get(pk=reservation_id)
    room = Room.objects.select_for_update().get(pk=room.pk)

    if reservation.status not in {Reservation.Status.CONFIRMED, Reservation.Status.PENDING}:
        raise ValidationError("Only pending or confirmed reservations can be checked in.")
    if hasattr(reservation, "stay"):
        raise ValidationError("This reservation already has a stay record.")
    if room.business_unit_id != reservation.business_unit_id or room.room_type_id != reservation.room_type_id:
        raise ValidationError("Selected room does not match this reservation.")
    if not room.is_ready:
        raise ValidationError("Selected room is not ready for check-in.")

    overlapping = Reservation.objects.filter(
        assigned_room=room,
        status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN],
        arrival_date__lt=reservation.departure_date,
        departure_date__gt=reservation.arrival_date,
    ).exclude(pk=reservation.pk)
    if overlapping.exists():
        raise ValidationError("The selected room has an overlapping active reservation.")

    reservation.assigned_room = room
    reservation.status = Reservation.Status.CHECKED_IN
    reservation.save(update_fields=["assigned_room", "status", "updated_at"])

    stay = Stay(
        reservation=reservation,
        guest=reservation.guest,
        room=room,
        checked_in_at=timezone.now(),
        checked_in_by=user,
        status=Stay.Status.IN_HOUSE,
    )
    stay.full_clean()
    stay.save()

    folio = Folio.objects.create(stay=stay)
    FolioCharge.objects.create(
        folio=folio,
        charge_type=FolioCharge.ChargeType.ROOM,
        description=f"Accommodation - {reservation.nights} night(s)",
        amount=reservation.accommodation_total,
        posted_by=user,
    )

    # Carry pre-arrival deposits into the active guest folio rather than counting them twice.
    reservation.payments.filter(status=Payment.Status.COMPLETED).update(folio=folio, reservation=None)

    room.occupancy_status = Room.Occupancy.OCCUPIED
    room.save(update_fields=["occupancy_status", "updated_at"])
    log_event(actor=user, business_unit=reservation.business_unit, module="hotel", action="check_in", description=f"Checked in {reservation.guest.full_name} to Room {room.number}.", reference_type="Stay", reference_id=stay.pk, reference_number=reservation.reservation_number)
    return stay


@transaction.atomic
def post_folio_payment(*, folio_id: int, amount, method: str, user, external_reference="", notes="") -> Payment:
    folio = Folio.objects.select_for_update().get(pk=folio_id)
    if folio.is_closed:
        raise ValidationError("This folio is already closed.")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError("Payment must be greater than zero.")
    payment = Payment(
        folio=folio,
        reference=f"HPT-{uuid.uuid4().hex[:12].upper()}",
        external_reference=external_reference,
        amount=amount,
        method=method,
        status=Payment.Status.COMPLETED,
        received_by=user,
        notes=notes,
    )
    payment.full_clean()
    payment.save()
    log_event(actor=user, business_unit=folio.stay.reservation.business_unit, module="hotel", action="payment", description=f"Received hotel payment {payment.reference}.", reference_type="Payment", reference_id=payment.pk, reference_number=payment.reference, new_values={"amount": str(payment.amount), "method": payment.method})
    return payment


@transaction.atomic
def check_out_stay(*, stay_id: int, user, allow_balance=False) -> Stay:
    stay = Stay.objects.select_for_update().select_related("reservation", "room").get(pk=stay_id)
    if stay.status != Stay.Status.IN_HOUSE:
        raise ValidationError("Only an in-house stay can be checked out.")
    folio = Folio.objects.select_for_update().get(stay=stay)
    if folio.balance > Decimal("0.00") and not allow_balance:
        raise ValidationError(f"Outstanding balance is ₦{folio.balance}. Receive payment before checkout.")

    now = timezone.now()
    stay.status = Stay.Status.CHECKED_OUT
    stay.checked_out_at = now
    stay.checked_out_by = user
    stay.save(update_fields=["status", "checked_out_at", "checked_out_by", "updated_at"])

    reservation = stay.reservation
    reservation.status = Reservation.Status.CHECKED_OUT
    reservation.save(update_fields=["status", "updated_at"])

    folio.is_closed = True
    folio.closed_at = now
    folio.save(update_fields=["is_closed", "closed_at", "updated_at"])

    room = stay.room
    room.occupancy_status = Room.Occupancy.VACANT
    room.housekeeping_status = Room.Housekeeping.DIRTY
    room.save(update_fields=["occupancy_status", "housekeeping_status", "updated_at"])
    HousekeepingTask.objects.create(room=room, task_type="Checkout Cleaning", status=HousekeepingTask.Status.PENDING)
    log_event(actor=user, business_unit=reservation.business_unit, module="hotel", action="check_out", description=f"Checked out {stay.guest.full_name} from Room {room.number}.", reference_type="Stay", reference_id=stay.pk, reference_number=reservation.reservation_number)
    return stay


@transaction.atomic
def verify_housekeeping_task(*, task_id: int, user) -> HousekeepingTask:
    task = HousekeepingTask.objects.select_for_update().select_related("room").get(pk=task_id)
    if task.status not in {HousekeepingTask.Status.COMPLETED, HousekeepingTask.Status.VERIFIED}:
        raise ValidationError("Only completed housekeeping tasks can be verified.")
    task.status = HousekeepingTask.Status.VERIFIED
    task.verified_by = user
    task.save(update_fields=["status", "verified_by", "updated_at"])

    room = task.room
    room.housekeeping_status = Room.Housekeeping.CLEAN
    room.save(update_fields=["housekeeping_status", "updated_at"])
    log_event(actor=user, business_unit=room.business_unit, module="housekeeping", action="verify", description=f"Verified Room {room.number} clean.", reference_type="HousekeepingTask", reference_id=task.pk, reference_number=str(task.pk))
    return task
