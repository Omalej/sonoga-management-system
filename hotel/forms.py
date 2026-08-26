import uuid

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Guest,
    HousekeepingTask,
    Payment,
    Reservation,
    Room,
)


class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "nationality",
            "identification_type",
            "identification_number",
            "preferences",
            "notes",
        ]


class ManualReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "business_unit",
            "source",
            "guest",
            "room_type",
            "arrival_date",
            "departure_date",
            "adults",
            "children",
            "nightly_rate",
            "discount_amount",
            "tax_amount",
            "special_requests",
        ]

        widgets = {
            "arrival_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "departure_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from organization.models import BusinessUnit
        from .models import RoomType

        self.fields["business_unit"].queryset = (
            BusinessUnit.objects.filter(
                unit_type=BusinessUnit.UnitType.HOTEL,
                is_active=True,
            )
        )

        self.fields["room_type"].queryset = (
            RoomType.objects.filter(
                business_unit__unit_type=BusinessUnit.UnitType.HOTEL,
                is_active=True,
            )
        )

        self.fields["source"].choices = [
            (value, label)
            for value, label in Reservation.Source.choices
            if value != Reservation.Source.WORDPRESS
        ]

    def save(self, user=None, commit=True):
        obj = super().save(commit=False)

        obj.reservation_number = (
            f"HMS-{uuid.uuid4().hex[:12].upper()}"
        )

        obj.status = Reservation.Status.CONFIRMED
        obj.created_by = user

        if commit:
            obj.full_clean()
            obj.save()

        return obj


class CheckInForm(forms.Form):
    room = forms.ModelChoiceField(
        queryset=Room.objects.none()
    )

    def __init__(
        self,
        *args,
        reservation=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.reservation = reservation

        if reservation:
            self.fields["room"].queryset = (
                Room.objects.filter(
                    business_unit=reservation.business_unit,
                    room_type=reservation.room_type,
                    occupancy_status=Room.Occupancy.VACANT,
                    housekeeping_status=Room.Housekeeping.CLEAN,
                    maintenance_status=Room.Maintenance.CLEAR,
                    is_blocked=False,
                )
                .order_by("number")
            )


class FolioPaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
    )

    method = forms.ChoiceField(
        choices=Payment.Method.choices
    )

    external_reference = forms.CharField(
        max_length=120,
        required=False,
    )

    notes = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 2}
        ),
        required=False,
    )


class HousekeepingUpdateForm(forms.ModelForm):
    class Meta:
        model = HousekeepingTask
        fields = [
            "assigned_to",
            "status",
            "priority",
            "notes",
        ]

    def clean_status(self):
        status = self.cleaned_data["status"]

        if (
            self.instance.status
            == HousekeepingTask.Status.VERIFIED
            and status != HousekeepingTask.Status.VERIFIED
        ):
            raise ValidationError(
                "A verified task cannot be reopened from this screen."
            )

        return status


class SwapGuestForm(forms.Form):
    new_guest = forms.ModelChoiceField(
        queryset=Guest.objects.none(),
        label="New Guest",
        empty_label="Select a guest",
    )

    def __init__(
        self,
        *args,
        reservation=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if reservation:
            self.fields["new_guest"].queryset = (
                Guest.objects
                .exclude(pk=reservation.guest_id)
                .order_by(
                    "last_name",
                    "first_name",
                )
            )