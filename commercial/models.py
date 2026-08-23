from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from core.models import TimeStampedModel
from organization.models import BusinessUnit
from inventory.models import Store
from factory.models import FactoryProduct


class Customer(TimeStampedModel):
    class CustomerType(models.TextChoices):
        DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
        WHOLESALER = "WHOLESALER", "Wholesaler"
        RETAILER = "RETAILER", "Retailer"
        SUPERMARKET = "SUPERMARKET", "Supermarket"
        RESTAURANT = "RESTAURANT", "Restaurant"
        HOTEL = "HOTEL", "Hotel"
        SCHOOL = "SCHOOL", "School"
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        CORPORATE = "CORPORATE", "Corporate"
        OTHER = "OTHER", "Other"

    customer_number = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=180)
    customer_type = models.CharField(max_length=30, choices=CustomerType.choices, default=CustomerType.RETAILER)
    business_units = models.ManyToManyField(BusinessUnit, related_name="factory_customers")
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.customer_number} - {self.name}"


class SalesInvoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        RETURNED = "RETURNED", "Returned"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="sales_invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales_invoices")
    fulfillment_store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="sales_invoices")
    salesperson = models.ForeignKey("hr.Employee", on_delete=models.PROTECT, related_name="sales_invoices")
    invoice_date = models.DateField()
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="factory_sales_created")

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        indexes = [models.Index(fields=["business_unit", "invoice_date", "status"])]

    def clean(self):
        errors = {}
        if self.business_unit_id and self.business_unit.unit_type not in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
            errors["business_unit"] = "Factory sales must belong to Water or Bread Factory."
        if self.fulfillment_store_id and self.business_unit_id and self.fulfillment_store.business_unit_id != self.business_unit_id:
            errors["fulfillment_store"] = "Fulfillment store must belong to the selected business unit."
        if self.salesperson_id and self.business_unit_id and self.salesperson.business_unit_id != self.business_unit_id:
            errors["salesperson"] = "Salesperson must belong to the selected business unit."
        if self.discount_amount is not None and self.discount_amount < 0:
            errors["discount_amount"] = "Discount cannot be negative."
        if errors:
            raise ValidationError(errors)

    @property
    def gross_total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0.00"))

    @property
    def net_total(self):
        return max(self.gross_total - self.discount_amount, Decimal("0.00"))

    @property
    def payments_total(self):
        return self.payments.filter(status=FactoryPayment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return self.net_total - self.payments_total

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class SalesInvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(FactoryProduct, on_delete=models.PROTECT, related_name="sales_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["invoice", "id"]

    def clean(self):
        errors = {}
        if self.product_id and self.invoice_id and self.product.business_unit_id != self.invoice.business_unit_id:
            errors["product"] = "Product must belong to the same business unit as the invoice."
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.unit_price is not None and self.unit_price < 0:
            errors["unit_price"] = "Unit price cannot be negative."
        if self.discount_amount is not None and self.discount_amount < 0:
            errors["discount_amount"] = "Line discount cannot be negative."
        if errors:
            raise ValidationError(errors)

    @property
    def line_total(self):
        return max((self.quantity * self.unit_price) - self.discount_amount, Decimal("0.00"))

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name}"


class FactoryPayment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        POS = "POS", "POS"
        TRANSFER = "TRANSFER", "Bank Transfer"
        CHEQUE = "CHEQUE", "Cheque"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        REVERSED = "REVERSED", "Reversed"

    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=80, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    external_reference = models.CharField(max_length=120, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="factory_payments_received")
    notes = models.TextField(blank=True)

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Payment amount must be greater than zero."})

    def __str__(self):
        return f"{self.reference} - {self.amount}"


class DistributionRoute(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vehicle(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    registration_number = models.CharField(max_length=30, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="vehicles")
    vehicle_type = models.CharField(max_length=80)
    driver = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_vehicles")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    def clean(self):
        if self.driver_id and self.driver.business_unit_id != self.business_unit_id:
            raise ValidationError({"driver": "Driver must belong to the same business unit as the vehicle."})

    def __str__(self):
        return self.registration_number


class Delivery(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        LOADED = "LOADED", "Loaded"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"
        PARTIAL = "PARTIAL", "Partially Delivered"
        RETURNED = "RETURNED", "Returned"
        CANCELLED = "CANCELLED", "Cancelled"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="deliveries")
    delivery_number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, null=True, blank=True, related_name="deliveries")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="deliveries")
    route = models.ForeignKey(DistributionRoute, on_delete=models.PROTECT, related_name="deliveries")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="deliveries")
    driver = models.ForeignKey("hr.Employee", on_delete=models.PROTECT, related_name="deliveries_driven")
    salesperson = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries_sold")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    loaded_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    expected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    collected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def clean(self):
        errors = {}
        if self.business_unit_id and self.business_unit.unit_type not in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
            errors["business_unit"] = "Distribution is currently for Water or Bread Factory."
        if self.invoice_id and self.invoice.business_unit_id != self.business_unit_id:
            errors["invoice"] = "Invoice must belong to the same business unit as the delivery."
        if self.vehicle_id and self.vehicle.business_unit_id != self.business_unit_id:
            errors["vehicle"] = "Vehicle must belong to the same business unit as the delivery."
        if self.driver_id and self.driver.business_unit_id != self.business_unit_id:
            errors["driver"] = "Driver must belong to the same business unit as the delivery."
        if self.salesperson_id and self.salesperson.business_unit_id != self.business_unit_id:
            errors["salesperson"] = "Salesperson must belong to the same business unit as the delivery."
        if self.collected_amount < 0 or self.expected_amount < 0:
            errors["collected_amount"] = "Amounts cannot be negative."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.delivery_number} - {self.customer.name}"


class DeliveryLine(TimeStampedModel):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(FactoryProduct, on_delete=models.PROTECT, related_name="delivery_lines")
    quantity_loaded = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_delivered = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_returned = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_damaged = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    def clean(self):
        errors = {}
        if self.product_id and self.delivery_id and self.product.business_unit_id != self.delivery.business_unit_id:
            errors["product"] = "Product must belong to the same business unit as the delivery."
        for field in ["quantity_loaded", "quantity_delivered", "quantity_returned", "quantity_damaged"]:
            value = getattr(self, field)
            if value is not None and value < 0:
                errors[field] = "Quantity cannot be negative."
        if self.quantity_loaded is not None and self.quantity_loaded <= 0:
            errors["quantity_loaded"] = "Loaded quantity must be greater than zero."
        if self.quantity_delivered + self.quantity_returned + self.quantity_damaged > self.quantity_loaded:
            errors["quantity_delivered"] = "Delivered + returned + damaged cannot exceed loaded quantity."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.delivery.delivery_number} - {self.product.name}"


class ProductReturn(TimeStampedModel):
    class Resolution(models.TextChoices):
        PENDING = "PENDING", "Pending Inspection"
        RESTOCK = "RESTOCK", "Restock"
        WRITE_OFF = "WRITE_OFF", "Write-off"

    return_number = models.CharField(max_length=50, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="product_returns")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="product_returns")
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, null=True, blank=True, related_name="returns")
    product = models.ForeignKey(FactoryProduct, on_delete=models.PROTECT, related_name="returns")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.TextField()
    resolution = models.CharField(max_length=20, choices=Resolution.choices, default=Resolution.PENDING)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="factory_returns_recorded")
    notes = models.TextField(blank=True)

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Return quantity must be greater than zero."
        if self.product_id and self.business_unit_id and self.product.business_unit_id != self.business_unit_id:
            errors["product"] = "Product must belong to the same business unit as the return."
        if self.invoice_id and self.business_unit_id and self.invoice.business_unit_id != self.business_unit_id:
            errors["invoice"] = "Invoice must belong to the same business unit as the return."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.return_number} - {self.product.name}"
