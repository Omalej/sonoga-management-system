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
    room = forms.ModelChoiceField(
        queryset=Room.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Room"
    )

    class Meta:
        model = Reservation
        fields = ['guest_name', 'room', 'room_type_name', 'check_in_date', 'check_out_date', 'status']
        widgets = {
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name of guest'}),
            'room_type_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard Room, Family Suite'}),
            'check_in_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.all().order_by('room_number')

    def save(self, commit=True):
        guest_name = self.cleaned_data.get('guest_name')
        guest, _ = Guest.objects.get_or_create(
            name=guest_name,
            defaults={'phone': 'WALK-IN'}
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
