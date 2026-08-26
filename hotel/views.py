import json
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from accounts.access import (
    HOTEL_MANAGER,
    RECEPTIONIST,
    HOUSEKEEPING,
    GROUP_MANAGEMENT,
    role_required,
    business_unit_for,
)

from organization.models import BusinessUnit

from .forms import (
    CheckInForm,
    FolioPaymentForm,
    GuestForm,
    HousekeepingUpdateForm,
    ManualReservationForm,
    SwapGuestForm,
)

from .models import (
    Guest,
    HousekeepingTask,
    Reservation,
    Room,
    Stay,
    RoomType,
)

from .services import (
    check_in_reservation,
    check_out_stay,
    post_folio_payment,
    verify_housekeeping_task,
    swap_guest,
)


# ============================================================
# HOTEL BUSINESS UNIT
# ============================================================

def _hotel_unit_for(user):
    """
    Return the hotel business unit assigned to the user.

    If the user's assigned business unit is not a hotel,
    fall back to the first active hotel business unit.
    """
    unit = business_unit_for(user)

    if unit and unit.unit_type == BusinessUnit.UnitType.HOTEL:
        return unit

    return (
        BusinessUnit.objects
        .filter(
            unit_type=BusinessUnit.UnitType.HOTEL,
            is_active=True,
        )
        .first()
    )


# ============================================================
# HOTEL DASHBOARD
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def hotel_dashboard(request):
    unit = _hotel_unit_for(request.user)

    if not unit:
        messages.warning(
            request,
            "No active hotel business unit is configured.",
        )
        return redirect("home")

    today = timezone.localdate()

    rooms = (
        Room.objects
        .filter(business_unit=unit)
        .select_related("room_type")
        .order_by("number")
    )

    arrivals = (
        Reservation.objects
        .filter(
            business_unit=unit,
            arrival_date=today,
            status__in=[
                Reservation.Status.PENDING,
                Reservation.Status.CONFIRMED,
            ],
        )
        .select_related(
            "guest",
            "room_type",
            "assigned_room",
        )
    )

    context = {
        "unit": unit,
        "rooms": rooms,
        "arrivals": arrivals,

        "occupied": rooms.filter(
            occupancy_status=Room.Occupancy.OCCUPIED
        ).count(),

        "ready": sum(
            1
            for room in rooms
            if room.is_ready
        ),

        "dirty": rooms.filter(
            housekeeping_status=Room.Housekeeping.DIRTY
        ).count(),

        "maintenance": rooms.exclude(
            maintenance_status=Room.Maintenance.CLEAR
        ).count(),
    }

    return render(
        request,
        "hotel/dashboard.html",
        context,
    )


# ============================================================
# RESERVATION LIST
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def reservation_list(request):
    unit = _hotel_unit_for(request.user)

    qs = (
        Reservation.objects
        .filter(business_unit=unit)
        .select_related(
            "guest",
            "room_type",
            "assigned_room",
        )
        .order_by("-created_at")
    )

    q = request.GET.get(
        "q",
        "",
    ).strip()

    if q:
        qs = qs.filter(
            Q(reservation_number__icontains=q)
            | Q(external_reference__icontains=q)
            | Q(guest__first_name__icontains=q)
            | Q(guest__last_name__icontains=q)
            | Q(guest__phone__icontains=q)
        )

    return render(
        request,
        "hotel/reservation_list.html",
        {
            "reservations": qs[:250],
            "q": q,
            "unit": unit,
        },
    )


# ============================================================
# CREATE GUEST
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def guest_create(request):
    form = GuestForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        guest = form.save()

        messages.success(
            request,
            f"Guest {guest.full_name} created.",
        )

        return redirect(
            "hotel:reservation_create"
        )

    return render(
        request,
        "layouts/form_page.html",
        {
            "form": form,
            "title": "Add Guest",
            "cancel_url": "/hotel/reservations/",
        },
    )


# ============================================================
# CREATE MANUAL RESERVATION
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def reservation_create(request):
    form = ManualReservationForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        reservation = form.save(
            user=request.user
        )

        messages.success(
            request,
            (
                f"Reservation "
                f"{reservation.reservation_number} "
                f"created."
            ),
        )

        return redirect(
            "hotel:reservation_detail",
            pk=reservation.pk,
        )

    return render(
        request,
        "layouts/form_page.html",
        {
            "form": form,
            "title": "New Manual Reservation",
            "help_text": (
                "Use this for walk-in, phone, WhatsApp, "
                "corporate or other offline reservations. "
                "Website bookings arrive from WordPress automatically."
            ),
            "cancel_url": "/hotel/reservations/",
        },
    )


# ============================================================
# RESERVATION DETAIL
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def reservation_detail(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            "guest",
            "room_type",
            "assigned_room",
            "business_unit",
        ),
        pk=pk,
    )

    payments = (
        reservation.payments
        .all()
        .order_by("created_at")
    )

    return render(
        request,
        "hotel/reservation_detail.html",
        {
            "reservation": reservation,
            "payments": payments,
        },
    )


# ============================================================
# SWAP GUEST
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def reservation_swap_guest(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            "guest",
            "room_type",
            "assigned_room",
            "business_unit",
        ),
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "hotel:reservation_detail",
            pk=reservation.pk,
        )

    form = SwapGuestForm(
        request.POST,
        reservation=reservation,
    )

    if not form.is_valid():
        messages.error(
            request,
            "Please select a valid guest.",
        )

        return redirect(
            "hotel:reservation_detail",
            pk=reservation.pk,
        )

    old_guest = reservation.guest
    new_guest = form.cleaned_data["new_guest"]

    try:
        swap_guest(
            reservation=reservation,
            new_guest=new_guest,
        )

    except ValidationError as exc:
        messages.error(
            request,
            "; ".join(exc.messages),
        )

    else:
        messages.success(
            request,
            (
                f"Guest successfully changed from "
                f"{old_guest.full_name} to "
                f"{new_guest.full_name}."
            ),
        )

    return redirect(
        "hotel:reservation_detail",
        pk=reservation.pk,
    )


# ============================================================
# CHECK-IN
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def reservation_checkin(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            "guest",
            "room_type",
            "business_unit",
        ),
        pk=pk,
    )

    form = CheckInForm(
        request.POST or None,
        reservation=reservation,
    )

    if request.method == "POST" and form.is_valid():

        try:
            stay = check_in_reservation(
                reservation_id=reservation.pk,
                room=form.cleaned_data["room"],
                user=request.user,
            )

        except ValidationError as exc:
            form.add_error(
                None,
                exc,
            )

        else:
            messages.success(
                request,
                (
                    f"{stay.guest.full_name} checked into "
                    f"Room {stay.room.number}."
                ),
            )

            return redirect(
                "hotel:stay_detail",
                pk=stay.pk,
            )

    return render(
        request,
        "layouts/form_page.html",
        {
            "form": form,
            "title": (
                f"Check In "
                f"{reservation.guest.full_name}"
            ),
            "cancel_url": (
                f"/hotel/reservations/"
                f"{reservation.pk}/"
            ),
        },
    )


# ============================================================
# STAY DETAIL
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def stay_detail(request, pk):
    stay = get_object_or_404(
        Stay.objects.select_related(
            "reservation",
            "guest",
            "room",
        ),
        pk=pk,
    )

    return render(
        request,
        "hotel/stay_detail.html",
        {
            "stay": stay,
        },
    )


# ============================================================
# FOLIO PAYMENT
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def folio_payment(request, pk):
    reservation = get_object_or_404(
        Reservation,
        pk=pk,
    )

    form = FolioPaymentForm(
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():

        try:
            post_folio_payment(
                reservation_id=reservation.pk,
                user=request.user,
                **form.cleaned_data,
            )

        except ValidationError as exc:
            form.add_error(
                None,
                exc,
            )

        else:
            messages.success(
                request,
                "Payment recorded.",
            )

            return redirect(
                "hotel:reservation_detail",
                pk=reservation.pk,
            )

    return render(
        request,
        "layouts/form_page.html",
        {
            "form": form,
            "title": "Receive Guest Payment",
            "cancel_url": (
                f"/hotel/reservations/"
                f"{reservation.pk}/"
            ),
        },
    )


# ============================================================
# CHECK-OUT
# ============================================================

@role_required(
    HOTEL_MANAGER,
    RECEPTIONIST,
    GROUP_MANAGEMENT,
)
def stay_checkout(request, pk):
    reservation = get_object_or_404(
        Reservation,
        pk=pk,
    )

    if request.method == "POST":

        try:
            check_out_stay(
                reservation_id=reservation.pk,
                user=request.user,
                allow_balance=request.user.is_superuser,
            )

        except ValidationError as exc:
            messages.error(
                request,
                "; ".join(exc.messages),
            )

        else:
            messages.success(
                request,
                (
                    "Guest checked out. "
                    "Housekeeping task created."
                ),
            )

            return redirect(
                "hotel:dashboard"
            )

    return render(
        request,
        "hotel/checkout_confirm.html",
        {
            "reservation": reservation,
        },
    )


# ============================================================
# HOUSEKEEPING LIST
# ============================================================

@role_required(
    HOUSEKEEPING,
    HOTEL_MANAGER,
    GROUP_MANAGEMENT,
)
def housekeeping_list(request):
    unit = _hotel_unit_for(request.user)

    tasks = (
        HousekeepingTask.objects
        .filter(
            room__business_unit=unit
        )
        .select_related(
            "room",
            "assigned_to",
        )
        .order_by(
            "status",
            "room__number",
        )
    )

    return render(
        request,
        "hotel/housekeeping_list.html",
        {
            "tasks": tasks,
            "unit": unit,
        },
    )


# ============================================================
# HOUSEKEEPING UPDATE
# ============================================================

@role_required(
    HOUSEKEEPING,
    HOTEL_MANAGER,
    GROUP_MANAGEMENT,
)
def housekeeping_update(request, pk):
    task = get_object_or_404(
        HousekeepingTask,
        pk=pk,
    )

    form = HousekeepingUpdateForm(
        request.POST or None,
        instance=task,
    )

    if request.method == "POST" and form.is_valid():

        task = form.save()

        if (
            task.status
            == HousekeepingTask.Status.CLEANING
        ):
            Room.objects.filter(
                pk=task.room_id
            ).update(
                housekeeping_status=(
                    Room.Housekeeping.CLEANING
                )
            )

        elif (
            task.status
            == HousekeepingTask.Status.COMPLETED
        ):
            Room.objects.filter(
                pk=task.room_id
            ).update(
                housekeeping_status=(
                    Room.Housekeeping.INSPECTION
                )
            )

        messages.success(
            request,
            "Housekeeping task updated.",
        )

        return redirect(
            "hotel:housekeeping"
        )

    return render(
        request,
        "layouts/form_page.html",
        {
            "form": form,
            "title": (
                f"Housekeeping - "
                f"Room {task.room.number}"
            ),
            "cancel_url": "/hotel/housekeeping/",
        },
    )


# ============================================================
# HOUSEKEEPING VERIFY
# ============================================================

@role_required(
    HOTEL_MANAGER,
    GROUP_MANAGEMENT,
)
def housekeeping_verify(request, pk):

    if request.method == "POST":

        try:
            verify_housekeeping_task(
                task_id=pk,
                user=request.user,
            )

        except ValidationError as exc:
            messages.error(
                request,
                "; ".join(exc.messages),
            )

        else:
            messages.success(
                request,
                (
                    "Room verified clean and returned "
                    "to ready status if maintenance is clear."
                ),
            )

    return redirect(
        "hotel:housekeeping"
    )


# ============================================================
# WORDPRESS BOOKING WEBHOOK
# ============================================================

@csrf_exempt
def wordpress_booking_webhook(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Invalid request method. "
                    "POST required."
                ),
            },
            status=405,
        )

    try:

        data = json.loads(request.body)

        # ====================================================
        # BOOKING REFERENCE
        # ====================================================

        ref = str(
            data.get("id")
            or data.get("booking_reference")
            or data.get("external_reference")
            or "WP-ORDER"
        )

        # ====================================================
        # BILLING
        # ====================================================

        billing = data.get(
            "billing",
            {},
        )

        if not isinstance(billing, dict):
            billing = {}

        guest_name = (
            f"{billing.get('first_name', '')} "
            f"{billing.get('last_name', '')}"
        ).strip()

        if not guest_name:
            guest_name = (
                data.get("guest_name")
                or "WordPress Guest"
            )

        guest_email = (
            billing.get("email")
            or data.get("email")
            or ""
        )

        guest_phone = (
            billing.get("phone")
            or data.get("phone")
            or ""
        )

        # ====================================================
        # GUEST NAME
        # ====================================================

        name_parts = guest_name.split(
            maxsplit=1
        )

        first_name = (
            name_parts[0]
            if name_parts
            else "WordPress"
        )

        last_name = (
            name_parts[1]
            if len(name_parts) > 1
            else "Guest"
        )

        # ====================================================
        # DATES
        # ====================================================

        raw_check_in = (
            data.get("check_in_date")
            or data.get("arrival_date")
            or data.get("date_created")
        )

        raw_check_out = (
            data.get("check_out_date")
            or data.get("departure_date")
        )

        check_in = (
            parse_date(
                str(raw_check_in)[:10]
            )
            if raw_check_in
            else timezone.localdate()
        )

        if not check_in:
            check_in = timezone.localdate()

        check_out = (
            parse_date(
                str(raw_check_out)[:10]
            )
            if raw_check_out
            else check_in + timedelta(days=1)
        )

        if not check_out:
            check_out = check_in + timedelta(days=1)

        if check_out <= check_in:
            check_out = check_in + timedelta(days=1)

        # ====================================================
        # ROOM TYPE
        # ====================================================

        room_type_name = (
            data.get("room_type")
            or data.get("room_type_name")
            or "Standard"
        )

        line_items = data.get(
            "line_items",
            [],
        )

        if (
            isinstance(line_items, list)
            and line_items
        ):
            first_item = line_items[0]

            if isinstance(first_item, dict):
                room_type_name = (
                    first_item.get("room_type")
                    or first_item.get("room_type_name")
                    or first_item.get("name")
                    or room_type_name
                )

        # ====================================================
        # HOTEL BUSINESS UNIT
        # ====================================================

        hotel_unit = (
            BusinessUnit.objects
            .filter(
                unit_type=BusinessUnit.UnitType.HOTEL,
                is_active=True,
            )
            .first()
        )

        if not hotel_unit:
            return JsonResponse(
                {
                    "status": "error",
                    "message": (
                        "No active hotel business "
                        "unit found."
                    ),
                },
                status=500,
            )

        # ====================================================
        # GUEST
        # ====================================================

        guest_lookup_phone = (
            guest_phone
            if guest_phone
            else f"WP-{ref}"
        )

        guest, created_guest = (
            Guest.objects.get_or_create(
                phone=guest_lookup_phone,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": guest_email,
                },
            )
        )

        # ====================================================
        # UPDATE EXISTING GUEST
        # ====================================================

        guest_changed = False

        if (
            guest_email
            and guest.email != guest_email
        ):
            guest.email = guest_email
            guest_changed = True

        if guest.first_name != first_name:
            guest.first_name = first_name
            guest_changed = True

        if guest.last_name != last_name:
            guest.last_name = last_name
            guest_changed = True

        if guest_changed:
            guest.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                    "updated_at",
                ]
            )

        # ====================================================
        # ROOM TYPE
        # ====================================================

        room_type = (
            RoomType.objects
            .filter(
                business_unit=hotel_unit,
                is_active=True,
                name__icontains=room_type_name,
            )
            .first()
        )

        # Try exact case-insensitive match.

        if not room_type:
            room_type = (
                RoomType.objects
                .filter(
                    business_unit=hotel_unit,
                    is_active=True,
                    name__iexact=room_type_name,
                )
                .first()
            )

        # Fallback to first active room type.

        if not room_type:
            room_type = (
                RoomType.objects
                .filter(
                    business_unit=hotel_unit,
                    is_active=True,
                )
                .first()
            )

        if not room_type:
            return JsonResponse(
                {
                    "status": "error",
                    "message": (
                        "No active room type is configured "
                        "for the hotel."
                    ),
                },
                status=500,
            )

        # ====================================================
        # PHYSICAL ROOM
        # ====================================================
        #
        # WordPress bookings receive a ROOM TYPE only.
        #
        # No physical room is automatically assigned.
        #
        # Reception selects the actual physical room
        # during check-in.
        #
        # This prevents duplicate room assignments.
        # ====================================================

        assigned_room = None

        # ====================================================
        # RESERVATION NUMBER
        # ====================================================

        reservation_number = (
            f"SNG-WP-"
            f"{ref[-6:] if len(ref) >= 6 else ref}"
        )

        # ====================================================
        # CREATE / UPDATE RESERVATION
        # ====================================================

        reservation, created = (
            Reservation.objects.update_or_create(
                source=Reservation.Source.WORDPRESS,
                external_reference=ref,
                defaults={
                    "business_unit": hotel_unit,
                    "reservation_number": reservation_number,
                    "guest": guest,
                    "room_type": room_type,
                    "assigned_room": assigned_room,
                    "arrival_date": check_in,
                    "departure_date": check_out,
                    "nightly_rate": room_type.base_rate,
                    "status": Reservation.Status.CONFIRMED,
                },
            )
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return JsonResponse(
            {
                "status": "success",
                "message": (
                    "Booking synchronized successfully "
                    "from SonogaHotels.com"
                ),
                "reservation_id": reservation.id,
                "reservation_number": (
                    reservation.reservation_number
                ),
                "external_reference": ref,
                "guest_id": guest.id,
                "guest_name": guest.full_name,
                "room_type": room_type.name,
                "check_in": str(check_in),
                "check_out": str(check_out),
                "nightly_rate": str(
                    room_type.base_rate
                ),
                "created": created,
                "guest_created": created_guest,
            },
            status=200,
        )

    # ========================================================
    # INVALID JSON
    # ========================================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON payload.",
            },
            status=400,
        )

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as exc:

        return JsonResponse(
            {
                "status": "error",
                "message": str(exc),
            },
            status=500,
        )