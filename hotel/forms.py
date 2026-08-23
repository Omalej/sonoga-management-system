from django import forms
from .models import Guest, Reservation, HousekeepingTask, Payment

class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ['name', 'email', 'phone', 'id_number']

class ManualReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['guest', 'guest_name', 'room', 'check_in_date', 'check_out_date', 'status']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CheckInForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['room', 'guest_name', 'check_in_date', 'check_out_date']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
        }

class FolioPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method']

class HousekeepingUpdateForm(forms.ModelForm):
    class Meta:
        model = HousekeepingTask
        fields = ['status', 'assigned_to']
