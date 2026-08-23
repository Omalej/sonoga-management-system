from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum, Case, When, F, DecimalField
from core.models import TimeStampedModel
from organization.models import BusinessUnit


class Store(TimeStampedModel):
    class StoreType(models.TextChoices):
        RAW_MATERIAL = "RAW_MATERIAL", "Raw Material"
        FINISHED_GOODS = "FINISHED_GOODS", "Finished Goods"
        GENERAL = "GENERAL", "General"
        KITCHEN = "KITCHEN", "Kitchen"
        BAR = "BAR", "Bar"
        HOUSEKEEPING = "HOUSEKEEPING", "Housekeeping"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="stores")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    store_type = models.CharField(max_length=30, choices=StoreType.choices, default=StoreType.GENERAL)
    location = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["business_unit__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="uniq_store_code_per_unit"),
            models.UniqueConstraint(fields=["business_unit", "name"], name="uniq_store_name_per_unit"),
        ]

    def __str__(self):
        return f"{self.business_unit.code} - {self.name}"


class Item(TimeStampedModel):
    class Category(models.TextChoices):
        RAW_MATERIAL = "RAW_MATERIAL", "Raw Material"
        FINISHED_PRODUCT = "FINISHED_PRODUCT", "Finished Product"
        PACKAGING = "PACKAGING", "Packaging"
        CONSUMABLE = "CONSUMABLE", "Consumable"
        FOOD = "FOOD", "Food"
        DRINK = "DRINK", "Drink"
        LINEN = "LINEN", "Linen"
        CLEANING = "CLEANING", "Cleaning"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OTHER = "OTHER", "Other"

    class Unit(models.TextChoices):
        PIECE = "PIECE", "Piece"
        BAG = "BAG", "Bag"
        CARTON = "CARTON", "Carton"
        ROLL = "ROLL", "Roll"
        KG = "KG", "Kilogram"
        GRAM = "GRAM", "Gram"
        LITRE = "LITRE", "Litre"
        ML = "ML", "Millilitre"
        PACK = "PACK", "Pack"
        LOAF = "LOAF", "Loaf"
        DOZEN = "DOZEN", "Dozen"
        UNIT = "UNIT", "Unit"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="inventory_items")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.UNIT)
    standard_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["business_unit__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="uniq_item_code_per_unit"),
            models.UniqueConstraint(fields=["business_unit", "name"], name="uniq_item_name_per_unit"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def balance_in_store(self, store):
        if store.business_unit_id != self.business_unit_id:
            return Decimal("0.000")
        movements = self.stock_movements.filter(store=store, is_void=False)
        result = movements.aggregate(
            total=Sum(
                Case(
                    When(direction=StockMovement.Direction.IN, then=F("quantity")),
                    When(direction=StockMovement.Direction.OUT, then=-F("quantity")),
                    default=Decimal("0.000"),
                    output_field=DecimalField(max_digits=18, decimal_places=3),
                )
            )
        )["total"]
        return result or Decimal("0.000")


class StockMovement(TimeStampedModel):
    class Direction(models.TextChoices):
        IN = "IN", "Stock In"
        OUT = "OUT", "Stock Out"

    class MovementType(models.TextChoices):
        OPENING = "OPENING", "Opening Balance"
        PURCHASE = "PURCHASE", "Purchase / Goods Receipt"
        PRODUCTION_ISSUE = "PRODUCTION_ISSUE", "Production Material Issue"
        PRODUCTION_OUTPUT = "PRODUCTION_OUTPUT", "Production Output"
        SALE = "SALE", "Sale"
        TRANSFER_IN = "TRANSFER_IN", "Transfer In"
        TRANSFER_OUT = "TRANSFER_OUT", "Transfer Out"
        RETURN_IN = "RETURN_IN", "Customer Return In"
        RETURN_OUT = "RETURN_OUT", "Supplier Return Out"
        DAMAGE = "DAMAGE", "Damage / Write-off"
        EXPIRY = "EXPIRY", "Expiry / Wastage"
        ADJUSTMENT_IN = "ADJUSTMENT_IN", "Adjustment In"
        ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Adjustment Out"

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="stock_movements")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="stock_movements")
    direction = models.CharField(max_length=10, choices=Direction.choices)
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reference = models.CharField(max_length=100, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_movements_posted")
    is_void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "item", "created_at"]),
            models.Index(fields=["reference"]),
        ]

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.store_id and self.item_id and self.store.business_unit_id != self.item.business_unit_id:
            errors["item"] = "Item and store must belong to the same business unit."
        if errors:
            raise ValidationError(errors)

    @property
    def signed_quantity(self):
        return self.quantity if self.direction == self.Direction.IN else -self.quantity

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.store} | {self.item} | {self.direction} {self.quantity}"
