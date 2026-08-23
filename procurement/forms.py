import uuid
from django import forms
from organization.models import BusinessUnit, Department
from inventory.models import Item, Store
from .models import (
    GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine,
    PurchaseRequest, PurchaseRequestLine, Supplier,
)


class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ["business_unit", "department", "required_date", "reason", "notes"]
        widgets = {"required_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            self.fields["business_unit"].queryset = BusinessUnit.objects.filter(pk=unit.pk)
            self.fields["business_unit"].initial = unit
        departments = Department.objects.filter(is_active=True)
        if unit and not user.is_superuser:
            departments = departments.filter(business_unit=unit)
        self.fields["department"].queryset = departments

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.request_number = obj.request_number or f"PR-{uuid.uuid4().hex[:12].upper()}"
        obj.requested_by = self.user
        obj.status = PurchaseRequest.Status.DRAFT
        if commit:
            obj.full_clean(); obj.save()
        return obj


class PurchaseRequestLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestLine
        fields = ["item", "quantity", "estimated_unit_cost", "notes"]

    def __init__(self, *args, purchase_request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.purchase_request = purchase_request
        if purchase_request:
            self.fields["item"].queryset = Item.objects.filter(business_unit=purchase_request.business_unit, is_active=True)

    def save(self, commit=True):
        obj = super().save(commit=False); obj.request = self.purchase_request
        if commit: obj.full_clean(); obj.save()
        return obj


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["business_unit", "request", "supplier", "order_date", "expected_delivery_date", "notes"]
        widgets = {"order_date": forms.DateInput(attrs={"type": "date"}), "expected_delivery_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs); self.user = user
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)
        self.fields["request"].queryset = PurchaseRequest.objects.filter(status=PurchaseRequest.Status.APPROVED)
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            self.fields["business_unit"].queryset = BusinessUnit.objects.filter(pk=unit.pk)
            self.fields["request"].queryset = self.fields["request"].queryset.filter(business_unit=unit)
            self.fields["business_unit"].initial = unit

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.order_number = obj.order_number or f"PO-{uuid.uuid4().hex[:12].upper()}"
        obj.created_by = self.user
        if commit: obj.full_clean(); obj.save()
        return obj


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["item", "quantity", "unit_cost"]

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs); self.order = order
        if order:
            self.fields["item"].queryset = Item.objects.filter(business_unit=order.business_unit, is_active=True)

    def save(self, commit=True):
        obj = super().save(commit=False); obj.order = self.order
        if commit: obj.full_clean(); obj.save()
        return obj


class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ["purchase_order", "destination_store", "received_date", "supplier_delivery_reference", "notes"]
        widgets = {"received_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs); self.user = user
        orders = PurchaseOrder.objects.filter(status__in=[PurchaseOrder.Status.ISSUED, PurchaseOrder.Status.PART_RECEIVED])
        stores = Store.objects.filter(is_active=True)
        unit = getattr(getattr(user, "employee", None), "business_unit", None) if user else None
        if unit and not user.is_superuser:
            orders = orders.filter(business_unit=unit); stores = stores.filter(business_unit=unit)
        self.fields["purchase_order"].queryset = orders
        self.fields["destination_store"].queryset = stores

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.receipt_number = obj.receipt_number or f"GRN-{uuid.uuid4().hex[:12].upper()}"
        obj.received_by = self.user
        if commit: obj.full_clean(); obj.save()
        return obj


class GoodsReceiptLineForm(forms.ModelForm):
    class Meta:
        model = GoodsReceiptLine
        fields = ["order_line", "quantity_received", "quantity_rejected"]

    def __init__(self, *args, receipt=None, **kwargs):
        super().__init__(*args, **kwargs); self.receipt = receipt
        if receipt:
            self.fields["order_line"].queryset = receipt.purchase_order.lines.select_related("item")

    def save(self, commit=True):
        obj = super().save(commit=False); obj.receipt = self.receipt
        if commit: obj.full_clean(); obj.save()
        return obj
