import uuid
from django import forms
from organization.models import BusinessUnit
from .models import PayrollLine, PayrollRun


class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ["business_unit", "period_start", "period_end", "notes"]
        widgets = {"period_start": forms.DateInput(attrs={"type": "date"}), "period_end": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            self.fields["business_unit"].queryset = BusinessUnit.objects.filter(pk=unit.pk)
            self.fields["business_unit"].initial = unit

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.payroll_number = obj.payroll_number or f"PAY-{uuid.uuid4().hex[:12].upper()}"
        obj.created_by = self.user
        if commit:
            obj.full_clean(); obj.save()
        return obj


class PayrollLineEditForm(forms.ModelForm):
    class Meta:
        model = PayrollLine
        fields = ["allowances", "overtime", "bonuses", "deductions", "payment_reference"]
