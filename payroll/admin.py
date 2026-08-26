from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import PayrollRun, PayrollLine
from .services import generate_payroll, approve_payroll, mark_payroll_paid


class PayrollLineInline(admin.TabularInline):
    model = PayrollLine
    extra = 0
    fields = ("employee", "basic_salary", "allowances", "overtime", "bonuses", "deductions", "gross_pay", "net_pay", "is_paid", "payment_reference")
    readonly_fields = ("gross_pay", "net_pay")


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ("payroll_number", "business_unit", "period_start", "period_end", "status", "net_total")
    list_filter = ("business_unit", "status")
    search_fields = ("payroll_number",)
    inlines = [PayrollLineInline]
    actions = ["generate_selected", "approve_selected", "mark_selected_paid"]

    @admin.action(description="Generate employee lines for selected payroll runs")
    def generate_selected(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                generate_payroll(payroll_run_id=obj.pk)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Generated {done} payroll run(s).")

    @admin.action(description="Approve selected generated payroll runs")
    def approve_selected(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                approve_payroll(payroll_run_id=obj.pk, approved_by=request.user)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Approved {done} payroll run(s).")

    @admin.action(description="Mark selected approved payroll runs as paid")
    def mark_selected_paid(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                mark_payroll_paid(payroll_run_id=obj.pk)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Marked {done} payroll run(s) paid.")
