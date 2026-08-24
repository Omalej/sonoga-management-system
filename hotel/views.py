from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Reservation, Room, Guest
from .forms import ManualReservationForm, GuestForm, CheckInForm, FolioPaymentForm, HousekeepingUpdateForm

@login_required
def reservation_create(request):
    if request.method == 'POST':
        form = ManualReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save()
            messages.success(request, f"Reservation for {reservation.guest.name} created successfully.")
            return redirect('hotel:reservation_list')
    else:
        form = ManualReservationForm()
    return render(request, 'hotel/reservation_form.html', {'form': form})

@login_required
def reservation_list(request):
    reservations = Reservation.objects.all().order_by('-created_at') if hasattr(Reservation, 'created_at') else Reservation.objects.all()
    return render(request, 'hotel/reservation_list.html', {'reservations': reservations})

@login_required
def room_list(request):
    rooms = Room.objects.all().order_by('room_number') if hasattr(Room, 'room_number') else Room.objects.all()
    return render(request, 'hotel/room_list.html', {'rooms': rooms})
