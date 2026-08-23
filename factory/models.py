from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from core.models import TimeStampedModel
from organization.models import BusinessUnit
from inventory.models import Item, Store


class FactoryProduct(TimeStampedModel):
    class ProductFamily(models.TextChoices):
        WATER = "WATER", "Water"
        BREAD = "BREAD", "Bread / Bakery"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="factory_products")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    product_family = models.CharField(max_length=20, choices=ProductFamily.choices)
    inventory_item = models.OneToOneField(Item, on_delete=models.PROTECT, related_name="factory_product")
    selling_price = models.DecimalField(max_digits=14, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    standard_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_stock = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["business_unit__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="uniq_factory_product_code_per_unit"),
            models.UniqueConstraint(fields=["business_unit", "name"], name="uniq_factory_product_name_per_unit"),
        ]

    def clean(self):
        errors = {}
        if self.business_unit_id:
            if self.business_unit.unit_type not in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
                errors["business_unit"] = "Factory products must belong to a Water or Bread business unit."
            expected = self.ProductFamily.WATER if self.business_unit.unit_type == BusinessUnit.UnitType.WATER else self.ProductFamily.BREAD
            if self.product_family and self.product_family != expected:
                errors["product_family"] = "Product family must match the selected business unit."
        if self.inventory_item_id and self.business_unit_id and self.inventory_item.business_unit_id != self.business_unit_id:
            errors["inventory_item"] = "Finished product inventory item must belong to the same business unit."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Recipe(TimeStampedModel):
    product = models.ForeignKey(FactoryProduct, on_delete=models.PROTECT, related_name="recipes")
    name = models.CharField(max_length=150)
    output_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    is_default = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["product__name", "name"]
        constraints = [models.UniqueConstraint(fields=["product", "name"], name="uniq_recipe_name_per_product")]

    def clean(self):
        if self.product_id and self.product.product_family != FactoryProduct.ProductFamily.BREAD:
            raise ValidationError({"product": "Recipes in this version are used for Bread Factory products."})
        if self.output_quantity is not None and self.output_quantity <= 0:
            raise ValidationError({"output_quantity": "Recipe output quantity must be greater than zero."})

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class RecipeLine(TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="recipe_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["recipe", "item__name"]
        constraints = [models.UniqueConstraint(fields=["recipe", "item"], name="uniq_recipe_item")]

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.recipe_id and self.item_id and self.recipe.product.business_unit_id != self.item.business_unit_id:
            errors["item"] = "Recipe material must belong to the same business unit as the product."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.recipe} - {self.item.name}"


class ProductionBatch(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PRODUCTION = "IN_PRODUCTION", "In Production"
        COMPLETED = "COMPLETED", "Completed"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="production_batches")
    batch_number = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(FactoryProduct, on_delete=models.PROTECT, related_name="production_batches")
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, null=True, blank=True, related_name="production_batches")
    raw_material_store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="production_material_batches")
    finished_goods_store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="production_output_batches")
    production_date = models.DateField()
    shift = models.CharField(max_length=60, blank=True)
    planned_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    produced_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    rejected_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    accepted_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    supervisor = models.ForeignKey("hr.Employee", on_delete=models.PROTECT, related_name="supervised_production_batches")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_production_batches")

    class Meta:
        ordering = ["-production_date", "-created_at"]
        indexes = [models.Index(fields=["business_unit", "production_date", "status"])]

    def clean(self):
        errors = {}
        if self.business_unit_id and self.business_unit.unit_type not in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
            errors["business_unit"] = "Production batches must belong to Water or Bread Factory."
        if self.product_id and self.business_unit_id and self.product.business_unit_id != self.business_unit_id:
            errors["product"] = "Product must belong to the selected business unit."
        if self.recipe_id and self.product_id and self.recipe.product_id != self.product_id:
            errors["recipe"] = "Recipe must belong to the selected product."
        if self.product_id and self.product.product_family == FactoryProduct.ProductFamily.BREAD and self.status not in {self.Status.PLANNED, self.Status.CANCELLED} and not self.recipe_id:
            errors["recipe"] = "Bread production requires a recipe before production begins."
        if self.raw_material_store_id and self.business_unit_id and self.raw_material_store.business_unit_id != self.business_unit_id:
            errors["raw_material_store"] = "Raw material store must belong to the selected business unit."
        if self.finished_goods_store_id and self.business_unit_id and self.finished_goods_store.business_unit_id != self.business_unit_id:
            errors["finished_goods_store"] = "Finished goods store must belong to the selected business unit."
        if self.supervisor_id and self.business_unit_id and self.supervisor.business_unit_id != self.business_unit_id:
            errors["supervisor"] = "Production supervisor must belong to the selected business unit."
        for field in ["planned_quantity", "produced_quantity", "rejected_quantity", "accepted_quantity"]:
            value = getattr(self, field)
            if value is not None and value < 0:
                errors[field] = "Quantity cannot be negative."
        if self.produced_quantity and self.rejected_quantity > self.produced_quantity:
            errors["rejected_quantity"] = "Rejected quantity cannot exceed produced quantity."
        if self.accepted_quantity and self.produced_quantity and self.accepted_quantity + self.rejected_quantity > self.produced_quantity:
            errors["accepted_quantity"] = "Accepted plus rejected quantity cannot exceed produced quantity."
        if errors:
            raise ValidationError(errors)

    @property
    def yield_percent(self):
        if not self.produced_quantity:
            return Decimal("0.00")
        return (self.accepted_quantity / self.produced_quantity * Decimal("100")).quantize(Decimal("0.01"))

    @property
    def wastage_percent(self):
        if not self.produced_quantity:
            return Decimal("0.00")
        return (self.rejected_quantity / self.produced_quantity * Decimal("100")).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.batch_number} - {self.product.name}"


class ProductionMaterialUsage(TimeStampedModel):
    batch = models.ForeignKey(ProductionBatch, on_delete=models.PROTECT, related_name="material_usages")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="production_usages")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["batch", "item__name"]
        constraints = [models.UniqueConstraint(fields=["batch", "item"], name="uniq_material_per_batch")]

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
        if self.batch_id and self.item_id and self.batch.business_unit_id != self.item.business_unit_id:
            errors["item"] = "Production material must belong to the same business unit as the batch."
        if errors:
            raise ValidationError(errors)

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.batch.batch_number} - {self.item.name}"


class BatchLoss(TimeStampedModel):
    class LossType(models.TextChoices):
        REJECT = "REJECT", "Production Reject"
        DAMAGE = "DAMAGE", "Damage"
        EXPIRY = "EXPIRY", "Expiry"
        RETURN_WRITE_OFF = "RETURN_WRITE_OFF", "Returned Product Write-off"
        OTHER = "OTHER", "Other"

    batch = models.ForeignKey(ProductionBatch, on_delete=models.PROTECT, related_name="losses")
    loss_type = models.CharField(max_length=30, choices=LossType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.TextField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="factory_losses_recorded")

    def clean(self):
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than zero."})

    def __str__(self):
        return f"{self.batch.batch_number} - {self.loss_type}"
