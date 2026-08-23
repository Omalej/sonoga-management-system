from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from core.models import TimeStampedModel
from organization.models import BusinessUnit, Department
from inventory.models import Item, Store


class Supplier(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.CharField(max_length=120, blank=True)
    bank_details = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PurchaseRequest(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ORDERED = "ORDERED", "Ordered"
        CANCELLED = "CANCELLED", "Cancelled"

    request_number = models.CharField(max_length=50, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="purchase_requests")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="purchase_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_requests_created")
    required_date = models.DateField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_requests_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.department_id and self.business_unit_id and self.department.business_unit_id != self.business_unit_id:
            raise ValidationError({"department": "Department must belong to the selected business unit."})

    @property
    def estimated_total(self):
        return sum((line.estimated_total for line in self.lines.all()), Decimal("0.00"))

    def __str__(self):
        return self.request_number


class PurchaseRequestLine(TimeStampedModel):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="purchase_request_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    estimated_unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.request_id and self.item_id and self.request.business_unit_id != self.item.business_unit_id:
            errors["item"] = "Item must belong to the request business unit."
        if errors:
            raise ValidationError(errors)

    @property
    def estimated_total(self):
        return self.quantity * self.estimated_unit_cost

    def __str__(self):
        return f"{self.request.request_number} - {self.item.name}"


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PART_RECEIVED = "PART_RECEIVED", "Part Received"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(max_length=50, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="purchase_orders")
    request = models.ForeignKey(PurchaseRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="purchase_orders")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_orders_created")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders_approved")
    notes = models.TextField(blank=True)

    @property
    def total_amount(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0.00"))

    def clean(self):
        if self.request_id and self.request.business_unit_id != self.business_unit_id:
            raise ValidationError({"request": "Purchase request must belong to the same business unit."})

    def __str__(self):
        return self.order_number


class PurchaseOrderLine(TimeStampedModel):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="purchase_order_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2)

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.unit_cost is not None and self.unit_cost < 0:
            errors["unit_cost"] = "Unit cost cannot be negative."
        if self.order_id and self.item_id and self.order.business_unit_id != self.item.business_unit_id:
            errors["item"] = "Item must belong to the purchase-order business unit."
        if errors:
            raise ValidationError(errors)

    @property
    def line_total(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.order.order_number} - {self.item.name}"


class GoodsReceipt(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted to Stock"
        CANCELLED = "CANCELLED", "Cancelled"

    receipt_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts")
    destination_store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="goods_receipts")
    received_date = models.DateField()
    supplier_delivery_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="goods_receipts_recorded")
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="goods_receipts_posted")
    notes = models.TextField(blank=True)

    def clean(self):
        if self.purchase_order_id and self.destination_store_id and self.purchase_order.business_unit_id != self.destination_store.business_unit_id:
            raise ValidationError({"destination_store": "Store must belong to the purchase-order business unit."})

    @property
    def accepted_total(self):
        return sum((line.accepted_value for line in self.lines.all()), Decimal("0.00"))

    def __str__(self):
        return self.receipt_number


class GoodsReceiptLine(TimeStampedModel):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines")
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_rejected = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    def clean(self):
        errors = {}
        if self.receipt_id and self.order_line_id and self.order_line.order_id != self.receipt.purchase_order_id:
            errors["order_line"] = "Order line must belong to the receipt purchase order."
        if self.quantity_received is not None and self.quantity_received <= 0:
            errors["quantity_received"] = "Received quantity must be greater than zero."
        if self.quantity_rejected is not None and self.quantity_rejected < 0:
            errors["quantity_rejected"] = "Rejected quantity cannot be negative."
        if self.quantity_received is not None and self.quantity_rejected is not None and self.quantity_rejected > self.quantity_received:
            errors["quantity_rejected"] = "Rejected quantity cannot exceed received quantity."
        if errors:
            raise ValidationError(errors)

    @property
    def accepted_quantity(self):
        return self.quantity_received - self.quantity_rejected

    @property
    def accepted_value(self):
        return self.accepted_quantity * self.order_line.unit_cost

    def __str__(self):
        return f"{self.receipt.receipt_number} - {self.order_line.item.name}"
