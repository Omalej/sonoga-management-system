from django.contrib import admin
from .models import BusinessUnit, Department, Position

@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit_type", "manager", "is_active")
    list_filter = ("unit_type", "is_active")
    search_fields = ("code", "name")

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "business_unit", "code", "is_active")
    list_filter = ("business_unit", "is_active")
    search_fields = ("name", "code")

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "business_unit", "reports_to", "is_active")
    list_filter = ("business_unit", "department", "is_active")
    search_fields = ("name",)
