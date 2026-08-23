from django.contrib import admin
from .models import PayrollRun, Payslip

@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'is_finalized', 'created_at')
    list_filter = ('year', 'is_finalized')

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_run', 'basic_salary', 'net_salary')
    list_filter = ('payroll_run', 'employee__business_unit')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__staff_number')
