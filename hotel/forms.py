from django import forms
from .models import Guest, Reservation, Room

class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ['name', 'email', 'phone', 'id_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ManualReservationForm(forms.ModelForm):
    guest_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name of guest'}))
    guest_phone = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    room = forms.ModelChoiceField(
        queryset=Room.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Room"
    )

    class Meta:
        model = Reservation
        fields = ['guest_name', 'guest_phone', 'room', 'room_type_name', 'arrival_date', 'departure_date', 'status']
        widgets = {
            'room_type_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard Room, Family Suite'}),
            'arrival_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'departure_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.all().order_by('room_number')

    def save(self, user=None, commit=True):
        guest_name = self.cleaned_data.get('guest_name')
        guest_phone = self.cleaned_data.get('guest_phone') or 'WALK-IN'
        guest, _ = Guest.objects.get_or_create(
            phone=guest_phone,
            defaults={'name': guest_name}
        )
        reservation = super().save(commit=False)
        reservation.guest = guest
        reservation.source = Reservation.Source.RECEPTION
        if commit:
            reservation.save()
        return reservation

class CheckInForm(forms.Form):
    room = forms.ModelChoiceField(queryset=Room.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        reservation = kwargs.pop('reservation', None)
        super().__init__(*args, **kwargs)
        if reservation and reservation.room:
            self.fields['room'].initial = reservation.room

class FolioPaymentForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    payment_method = forms.CharField(max_length=50, initial='Cash', widget=forms.TextInput(attrs={'class': 'form-control'}))
    reference = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

class HousekeepingUpdateForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = []
