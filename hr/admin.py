from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("staff_number", "full_name", "business_unit", "department", "position", "status")
    list_filter = ("business_unit", "department", "status", "employment_type")
    search_fields = ("staff_number", "first_name", "middle_name", "last_name", "phone", "email")
