import uuid
from django import forms
from organization.models import BusinessUnit
from .models import Item, Store, StockMovement


class StockAdjustmentForm(forms.Form):
    business_unit = forms.ModelChoiceField(queryset=BusinessUnit.objects.filter(is_active=True))
    store = forms.ModelChoiceField(queryset=Store.objects.none())
    item = forms.ModelChoiceField(queryset=Item.objects.none())
    adjustment = forms.ChoiceField(choices=[("IN", "Increase stock"), ("OUT", "Decrease stock")])
    quantity = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    reference = forms.CharField(max_length=100, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            self.fields["business_unit"].queryset = BusinessUnit.objects.filter(pk=unit.pk)
            self.fields["business_unit"].initial = unit
        allowed_units = BusinessUnit.objects.filter(is_active=True)
        if unit and not user.is_superuser:
            allowed_units = allowed_units.filter(pk=unit.pk)
        self.fields["store"].queryset = Store.objects.filter(business_unit__in=allowed_units, is_active=True)
        self.fields["item"].queryset = Item.objects.filter(business_unit__in=allowed_units, is_active=True)

    def clean(self):
        cleaned = super().clean()
        unit, store, item = cleaned.get("business_unit"), cleaned.get("store"), cleaned.get("item")
        if unit and store and store.business_unit_id != unit.id:
            self.add_error("store", "Store must belong to the selected business unit.")
        if unit and item and item.business_unit_id != unit.id:
            self.add_error("item", "Item must belong to the selected business unit.")
        return cleaned


class StockTransferForm(forms.Form):
    item = forms.ModelChoiceField(queryset=Item.objects.filter(is_active=True))
    source_store = forms.ModelChoiceField(queryset=Store.objects.filter(is_active=True))
    destination_store = forms.ModelChoiceField(queryset=Store.objects.filter(is_active=True))
    quantity = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    reference = forms.CharField(max_length=100, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            self.fields["item"].queryset = Item.objects.filter(business_unit=unit, is_active=True)
            self.fields["source_store"].queryset = Store.objects.filter(business_unit=unit, is_active=True)
            self.fields["destination_store"].queryset = Store.objects.filter(business_unit=unit, is_active=True)
