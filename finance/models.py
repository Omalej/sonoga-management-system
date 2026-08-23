from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from core.models import TimeStampedModel
from organization.models import BusinessUnit, Department
from procurement.models import Supplier


class ExpenseCategory(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    expense_number = models.CharField(max_length=50, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="expenses")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True, related_name="expenses")
    expense_date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_requested")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    supporting_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        indexes = [models.Index(fields=["business_unit", "expense_date", "status"])]

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Expense amount must be greater than zero."
        if self.department_id and self.business_unit_id and self.department.business_unit_id != self.business_unit_id:
            errors["department"] = "Department must belong to the selected business unit."
        if errors:
            raise ValidationError(errors)

    @property
    def payments_total(self):
        return self.payments.filter(status=ExpensePayment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return max(self.amount - self.payments_total, Decimal("0.00"))

    def __str__(self):
        return f"{self.expense_number} - {self.description}"


class ExpensePayment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        POS = "POS", "POS"
        TRANSFER = "TRANSFER", "Bank Transfer"
        CHEQUE = "CHEQUE", "Cheque"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        REVERSED = "REVERSED", "Reversed"

    expense = models.ForeignKey(Expense, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=80, unique=True)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expense_payments_made")
    external_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Payment amount must be greater than zero."})

    def __str__(self):
        return f"{self.reference} - {self.amount}"


class SupplierInvoice(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice_number = models.CharField(max_length=80)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="supplier_invoices")
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="supplier_invoices")
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    purchase_order = models.ForeignKey("procurement.PurchaseOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="supplier_invoices")
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["supplier", "invoice_number"], name="uniq_supplier_invoice_number")]

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Invoice amount must be greater than zero."})
        if self.purchase_order_id and self.purchase_order.business_unit_id != self.business_unit_id:
            raise ValidationError({"purchase_order": "Purchase order must belong to the same business unit."})

    def __str__(self):
        return f"{self.supplier.name} - {self.invoice_number}"
