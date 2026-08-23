from django.contrib import admin
from .models import Employee, LeaveRequest

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("staff_number", "first_name", "last_name", "business_unit", "department", "status", "state_of_origin")
    list_filter = ("business_unit", "department", "status", "employment_type", "state_of_origin")
    search_fields = ("staff_number", "first_name", "middle_name", "last_name", "phone", "email", "state_of_origin", "lga")

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status', 'start_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__staff_number')
