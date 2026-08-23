import uuid
from django import forms
from organization.models import Department
from procurement.models import Supplier
from .models import Expense, ExpenseCategory, ExpensePayment


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["business_unit", "department", "category", "supplier", "expense_date", "description", "amount", "supporting_reference", "notes"]
        widgets = {"expense_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and hasattr(user, "employee") and not user.is_superuser:
            unit = user.employee.business_unit
            self.fields["business_unit"].queryset = self.fields["business_unit"].queryset.filter(pk=unit.pk)
            self.fields["business_unit"].initial = unit
            self.fields["department"].queryset = Department.objects.filter(business_unit=unit, is_active=True)
            self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.expense_number = f"EXP-{uuid.uuid4().hex[:12].upper()}"
        obj.requested_by = self.user
        obj.status = Expense.Status.SUBMITTED
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class ExpensePaymentForm(forms.Form):
    payment_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(choices=ExpensePayment.Method.choices)
    external_reference = forms.CharField(max_length=120, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
