import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Reservation, Room, Guest
from .forms import ManualReservationForm

@login_required
def hotel_dashboard(request):
    total_rooms = Room.objects.count()
    occupied_rooms = Room.objects.filter(status='Occupied').count()
    available_rooms = Room.objects.filter(status='Available').count()
    context = {
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'available_rooms': available_rooms,
    }
    return render(request, 'hotel/dashboard.html', context)

@login_required
def reservation_list(request):
    q = request.GET.get('q', '')
    reservations = Reservation.objects.all().order_by('-check_in_date')
    if q:
        reservations = reservations.filter(reservation_number__icontains=q) | reservations.filter(guest_name__icontains=q)
    return render(request, 'hotel/reservation_list.html', {'reservations': reservations, 'q': q})

@login_required
def manual_reservation(request):
    if request.method == 'POST':
        form = ManualReservationForm(request.POST)
        if form.is_valid():
            res = form.save(commit=False)
            res.reservation_number = f"SNG-{Room.objects.count() + 1000}"
            res.source = 'Direct'
            res.save()
            messages.success(request, 'Reservation successfully created by Receptionist!')
            return redirect('hotel:reservation_list')
    else:
        form = ManualReservationForm()
    return render(request, 'hotel/reservation_form.html', {'form': form})

@login_required
def sync_wordpress_bookings(request):
    sample_wp_ref = f"WP-BOOKING-{Room.objects.count() + 500}"
    room = Room.objects.first()
    if room:
        Reservation.objects.get_or_create(
            external_reference=sample_wp_ref,
            defaults={
                'reservation_number': sample_wp_ref,
                'source': 'WordPress',
                'room': room,
                'guest_name': 'Web Visitor (WordPress)',
                'check_in_date': '2026-09-01',
                'check_out_date': '2026-09-03',
                'status': 'Confirmed'
            }
        )
        messages.success(request, 'Successfully synchronized latest bookings from WordPress frontend!')
    else:
        messages.warning(request, 'Please create at least one Room in the database before syncing WordPress bookings.')
    return redirect('hotel:reservation_list')

@csrf_exempt
def wordpress_booking_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ref = data.get('booking_reference') or data.get('external_reference')
            guest_name = data.get('guest_name') or 'WordPress Guest'
            guest_email = data.get('email', '')
            guest_phone = data.get('phone', '')
            check_in = data.get('check_in_date')
            check_out = data.get('check_out_date')
            room_type_name = data.get('room_type', 'Standard')

            if not ref or not check_in or not check_out:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields (reference, check_in, check_out)'}, status=400)

            guest, _ = Guest.objects.get_or_create(
                phone=guest_phone or 'N/A',
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
