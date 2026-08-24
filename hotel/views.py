import json
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from accounts.access import HOTEL_MANAGER, RECEPTIONIST, HOUSEKEEPING, GROUP_MANAGEMENT, role_required, business_unit_for
from organization.models import BusinessUnit
from .forms import CheckInForm, FolioPaymentForm, GuestForm, HousekeepingUpdateForm, ManualReservationForm
from .models import Guest, HousekeepingTask, Reservation, Room, FolioCharge, Payment
from .services import check_in_reservation, check_out_stay, post_folio_payment, verify_housekeeping_task

def _hotel_unit_for(user):
    unit = business_unit_for(user)
    if unit and unit.unit_type == BusinessUnit.UnitType.HOTEL:
        return unit
    return BusinessUnit.objects.filter(unit_type=BusinessUnit.UnitType.HOTEL, is_active=True).first()

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def hotel_dashboard(request):
    unit = _hotel_unit_for(request.user)
    if not unit:
        messages.warning(request, "No active hotel business unit is configured.")
        return redirect("home")
    today = timezone.localdate()
    rooms = Room.objects.filter(business_unit=unit).select_related("room_type").order_by("number")
    arrivals = Reservation.objects.filter(business_unit=unit, arrival_date=today, status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED]).select_related("guest", "room_type", "assigned_room")
    context = {
        "unit": unit,
        "rooms": rooms,
        "arrivals": arrivals,
        "occupied": rooms.filter(occupancy_status=Room.Occupancy.OCCUPIED).count(),
        "ready": sum(1 for room in rooms if room.is_ready),
        "dirty": rooms.filter(housekeeping_status=Room.Housekeeping.DIRTY).count(),
        "maintenance": rooms.exclude(maintenance_status=Room.Maintenance.CLEAR).count(),
    }
    return render(request, "hotel/dashboard.html", context)

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def reservation_list(request):
    unit = _hotel_unit_for(request.user)
    qs = Reservation.objects.filter(business_unit=unit).select_related("guest", "room_type", "assigned_room").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(reservation_number__icontains=q) | Q(external_reference__icontains=q) | Q(guest__first_name__icontains=q) | Q(guest__last_name__icontains=q) | Q(guest__phone__icontains=q))
    return render(request, "hotel/reservation_list.html", {"reservations": qs[:250], "q": q, "unit": unit})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def guest_create(request):
    form = GuestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        guest = form.save()
        messages.success(request, f"Guest {guest.full_name} created.")
        return redirect("hotel:reservation_create")
    return render(request, "layouts/form_page.html", {"form": form, "title": "Add Guest", "cancel_url": "/hotel/reservations/"})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def reservation_create(request):
    form = ManualReservationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reservation = form.save(user=request.user)
        messages.success(request, f"Reservation {reservation.reservation_number} created.")
        return redirect("hotel:reservation_detail", pk=reservation.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "New Manual Reservation", "help_text": "Use this for walk-in, phone, WhatsApp, corporate or other offline reservations. Website bookings arrive from WordPress automatically.", "cancel_url": "/hotel/reservations/"})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def reservation_detail(request, pk):
    reservation = get_object_or_404(Reservation.objects.select_related("guest", "room_type", "assigned_room", "business_unit"), pk=pk)
    payments = reservation.payments.all().order_by("created_at")
    return render(request, "hotel/reservation_detail.html", {"reservation": reservation, "payments": payments})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def reservation_checkin(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    form = CheckInForm(request.POST or None, reservation=reservation)
    if request.method == "POST" and form.is_valid():
        try:
            stay = check_in_reservation(reservation_id=reservation.pk, room=form.cleaned_data["room"], user=request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{stay.guest.full_name} checked into Room {stay.room.number}.")
            return redirect("hotel:stay_detail", pk=stay.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Check In {reservation.guest.full_name}", "cancel_url": f"/hotel/reservations/{reservation.pk}/"})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def stay_detail(request, pk):
    stay = get_object_or_404(Reservation.objects.select_related("guest", "assigned_room"), pk=pk)
    return render(request, "hotel/stay_detail.html", {"stay": stay})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def folio_payment(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    form = FolioPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            post_folio_payment(reservation_id=reservation.pk, user=request.user, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Payment recorded.")
            return redirect("hotel:reservation_detail", pk=reservation.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "Receive Guest Payment", "cancel_url": f"/hotel/reservations/{reservation.pk}/"})

@role_required(HOTEL_MANAGER, RECEPTIONIST, GROUP_MANAGEMENT)
def stay_checkout(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == "POST":
        try:
            check_out_stay(reservation_id=reservation.pk, user=request.user, allow_balance=request.user.is_superuser)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Guest checked out. Housekeeping task created.")
            return redirect("hotel:dashboard")
    return render(request, "hotel/checkout_confirm.html", {"reservation": reservation})

@role_required(HOUSEKEEPING, HOTEL_MANAGER, GROUP_MANAGEMENT)
def housekeeping_list(request):
    unit = _hotel_unit_for(request.user)
    tasks = HousekeepingTask.objects.filter(room__business_unit=unit).select_related("room", "assigned_to").order_by("status", "room__number")
    return render(request, "hotel/housekeeping_list.html", {"tasks": tasks, "unit": unit})

@role_required(HOUSEKEEPING, HOTEL_MANAGER, GROUP_MANAGEMENT)
def housekeeping_update(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    form = HousekeepingUpdateForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        if task.status == HousekeepingTask.Status.CLEANING:
            Room.objects.filter(pk=task.room_id).update(housekeeping_status=Room.Housekeeping.CLEANING)
        elif task.status == HousekeepingTask.Status.COMPLETED:
            Room.objects.filter(pk=task.room_id).update(housekeeping_status=Room.Housekeeping.INSPECTION)
        messages.success(request, "Housekeeping task updated.")
        return redirect("hotel:housekeeping")
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Housekeeping - Room {task.room.number}", "cancel_url": "/hotel/housekeeping/"})

@role_required(HOTEL_MANAGER, GROUP_MANAGEMENT)
def housekeeping_verify(request, pk):
    if request.method == "POST":
        try:
            verify_housekeeping_task(task_id=pk, user=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Room verified clean and returned to ready status if maintenance is clear.")
    return redirect("hotel:housekeeping")

@csrf_exempt
def wordpress_booking_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ref = str(data.get('id') or data.get('booking_reference') or data.get('external_reference') or 'WP-ORDER')
            billing = data.get('billing', {})
            guest_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip() or data.get('guest_name') or 'WordPress Guest'
            guest_email = billing.get('email') or data.get('email', '')
            guest_phone = billing.get('phone') or data.get('phone', '')
            
            raw_check_in = data.get('check_in_date') or data.get('date_created')
            raw_check_out = data.get('check_out_date')
            
            check_in = parse_date(str(raw_check_in)[:10]) if raw_check_in else timezone.now().date()
            check_out = parse_date(str(raw_check_out)[:10]) if raw_check_out else (timezone.now().date() + timedelta(days=1))
            
            if not check_in:
                check_in = timezone.now().date()
            if not check_out:
                check_out = check_in + timedelta(days=1)

            room_type_name = 'Standard'
            line_items = data.get('line_items', [])
            if line_items:
                room_type_name = line_items[0].get('name', 'Standard')
            else:
                room_type_name = data.get('room_type', 'Standard')

            guest, _ = Guest.objects.get_or_create(
                phone=guest_phone if guest_phone else f'WP-{ref}',
                defaults={'name': guest_name, 'email': guest_email}
            )

            room = Room.objects.filter(room_type__icontains=room_type_name, status='Available').first() or Room.objects.first()

            reservation, created = Reservation.objects.update_or_create(
                external_reference=ref,
                defaults={
                    'reservation_number': f"SNG-WP-{ref[-6:] if len(ref) >= 6 else ref}",
                    'source': 'WordPress',
                    'guest': guest,
                    'guest_name': guest_name,
                    'room': room,
                    'check_in_date': check_in,
                    'check_out_date': check_out,
                    'status': 'Confirmed'
                }
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Booking synchronized successfully from SonogaHotels.com',
                'reservation_id': reservation.id
            }, status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method. POST required.'}, status=405)
