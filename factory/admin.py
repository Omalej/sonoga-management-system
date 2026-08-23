from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import FactoryProduct, Recipe, RecipeLine, ProductionBatch, ProductionMaterialUsage, BatchLoss
from .services import approve_production_batch


class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 1


@admin.register(FactoryProduct)
class FactoryProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "business_unit", "product_family", "selling_price", "standard_cost", "shelf_life_days", "is_active")
    list_filter = ("business_unit", "product_family", "is_active")
    search_fields = ("code", "name")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "output_quantity", "is_default", "is_active")
    list_filter = ("product__business_unit", "is_default", "is_active")
    search_fields = ("name", "product__name")
    inlines = [RecipeLineInline]


@admin.register(RecipeLine)
class RecipeLineAdmin(admin.ModelAdmin):
    list_display = ("recipe", "item", "quantity")
    list_filter = ("recipe__product__business_unit",)
    search_fields = ("recipe__name", "item__name", "item__code")


class ProductionMaterialUsageInline(admin.TabularInline):
    model = ProductionMaterialUsage
    extra = 1


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "business_unit", "product", "production_date", "planned_quantity", "accepted_quantity", "rejected_quantity", "yield_percent", "status")
    list_filter = ("business_unit", "product", "status", "production_date")
    search_fields = ("batch_number", "product__name")
    date_hierarchy = "production_date"
    inlines = [ProductionMaterialUsageInline]
    actions = ["approve_selected_batches"]

    @admin.action(description="Approve selected production batches and post stock")
    def approve_selected_batches(self, request, queryset):
        approved = 0
        for batch in queryset:
            try:
                approve_production_batch(batch_id=batch.pk, approved_by=request.user)
                approved += 1
            except ValidationError as exc:
                self.message_user(request, f"{batch.batch_number}: {exc}", level=messages.ERROR)
        if approved:
            self.message_user(request, f"Approved {approved} production batch(es).", level=messages.SUCCESS)


@admin.register(ProductionMaterialUsage)
class ProductionMaterialUsageAdmin(admin.ModelAdmin):
    list_display = ("batch", "item", "quantity", "unit_cost", "total_cost")
    list_filter = ("batch__business_unit",)
    search_fields = ("batch__batch_number", "item__name", "item__code")


@admin.register(BatchLoss)
class BatchLossAdmin(admin.ModelAdmin):
    list_display = ("batch", "loss_type", "quantity", "recorded_by", "created_at")
    list_filter = ("batch__business_unit", "loss_type")
    search_fields = ("batch__batch_number", "reason")
