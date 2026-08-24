from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Reservation, Room, FolioCharge, Payment, HousekeepingTask, Guest

def check_in_reservation(reservation_id, room, user=None):
    reservation = Reservation.objects.get(pk=reservation_id)
    reservation.assigned_room = room
    reservation.status = 'Checked-In'
    reservation.save()
    Room.objects.filter(pk=room.pk).update(occupancy_status='Occupied')
    return reservation

def check_out_stay(reservation_id, user=None, allow_balance=False):
    reservation = Reservation.objects.get(pk=reservation_id)
    reservation.status = 'Checked-Out'
    reservation.save()
    if reservation.assigned_room:
        Room.objects.filter(pk=reservation.assigned_room.pk).update(occupancy_status='Vacant', housekeeping_status='Dirty')
        HousekeepingTask.objects.create(
            room=reservation.assigned_room,
            task_type='Cleaning',
            status='Pending',
            notes=f'Checkout cleaning for reservation {reservation.reservation_number}'
        )
    return reservation

def post_folio_payment(reservation_id, user=None, amount=0, payment_method='Cash', reference=''):
    reservation = Reservation.objects.get(pk=reservation_id)
    payment = Payment.objects.create(
        reservation=reservation,
        amount=amount,
        payment_method=payment_method,
        reference=reference
    )
    return payment

def verify_housekeeping_task(task_id, user=None):
    task = HousekeepingTask.objects.get(pk=task_id)
    task.status = 'Completed'
    task.save()
    Room.objects.filter(pk=task.room.pk).update(housekeeping_status='Ready')
    return task
