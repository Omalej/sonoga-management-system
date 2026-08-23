from django.contrib import admin
from .models import Store, Item, StockMovement


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "business_unit", "store_type", "is_active")
    list_filter = ("business_unit", "store_type", "is_active")
    search_fields = ("code", "name", "location")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "business_unit", "category", "unit", "standard_cost", "reorder_level", "is_active")
    list_filter = ("business_unit", "category", "unit", "is_active")
    search_fields = ("code", "name")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("item", "store", "direction", "movement_type", "quantity", "unit_cost", "reference", "posted_by", "created_at", "is_void")
    list_filter = ("store__business_unit", "store", "direction", "movement_type", "is_void")
    search_fields = ("item__code", "item__name", "reference", "notes")
    date_hierarchy = "created_at"
