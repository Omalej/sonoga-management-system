import uuid
from django import forms
from commercial.models import Customer, FactoryPayment, SalesInvoice, SalesInvoiceLine
from hr.models import Employee
from inventory.models import Store
from .models import FactoryProduct, ProductionBatch, ProductionMaterialUsage, Recipe


class ProductionBatchForm(forms.ModelForm):
    class Meta:
        model = ProductionBatch
        fields = ["product", "recipe", "raw_material_store", "finished_goods_store", "production_date", "shift", "planned_quantity", "produced_quantity", "rejected_quantity", "accepted_quantity", "supervisor", "status", "notes"]
        widgets = {"production_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, business_unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business_unit = business_unit
        if business_unit:
            self.fields["product"].queryset = FactoryProduct.objects.filter(business_unit=business_unit, is_active=True)
            self.fields["recipe"].queryset = Recipe.objects.filter(product__business_unit=business_unit, is_active=True)
            self.fields["raw_material_store"].queryset = Store.objects.filter(business_unit=business_unit, is_active=True)
            self.fields["finished_goods_store"].queryset = Store.objects.filter(business_unit=business_unit, is_active=True)
            self.fields["supervisor"].queryset = Employee.objects.filter(business_unit=business_unit, status=Employee.Status.ACTIVE)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.business_unit = self.business_unit
        if not obj.batch_number:
            prefix = "WAT" if self.business_unit.unit_type == self.business_unit.UnitType.WATER else "BRD"
            obj.batch_number = f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class ProductionMaterialUsageForm(forms.ModelForm):
    class Meta:
        model = ProductionMaterialUsage
        fields = ["item", "quantity", "unit_cost", "notes"]

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch
        if batch:
            self.fields["item"].queryset = batch.business_unit.inventory_items.filter(is_active=True).exclude(category="FINISHED_PRODUCT")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.batch = self.batch
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class SalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = ["customer", "fulfillment_store", "salesperson", "invoice_date", "discount_amount", "due_date", "notes"]
        widgets = {"invoice_date": forms.DateInput(attrs={"type": "date"}), "due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, business_unit=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business_unit = business_unit
        self.user = user
        if business_unit:
            self.fields["customer"].queryset = Customer.objects.filter(business_units=business_unit, is_active=True).distinct()
            self.fields["fulfillment_store"].queryset = Store.objects.filter(business_unit=business_unit, is_active=True)
            self.fields["salesperson"].queryset = Employee.objects.filter(business_unit=business_unit, status=Employee.Status.ACTIVE)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.business_unit = self.business_unit
        obj.invoice_number = f"SAL-{uuid.uuid4().hex[:12].upper()}"
        obj.created_by = self.user
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class SalesInvoiceLineForm(forms.ModelForm):
    class Meta:
        model = SalesInvoiceLine
        fields = ["product", "quantity", "unit_price", "discount_amount"]

    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        if invoice:
            self.fields["product"].queryset = FactoryProduct.objects.filter(business_unit=invoice.business_unit, is_active=True)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.invoice = self.invoice
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class FactoryPaymentForm(forms.Form):
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(choices=FactoryPayment.Method.choices)
    external_reference = forms.CharField(max_length=120, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
