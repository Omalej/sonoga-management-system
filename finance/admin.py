from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import ExpenseCategory, Expense, ExpensePayment, SupplierInvoice
from .services import approve_expense


class ExpensePaymentInline(admin.TabularInline):
    model = ExpensePayment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_number", "business_unit", "department", "category", "amount", "status", "expense_date")
    list_filter = ("business_unit", "department", "category", "status")
    search_fields = ("expense_number", "description", "supplier__name")
    inlines = [ExpensePaymentInline]
    actions = ["approve_selected"]

    @admin.action(description="Approve selected submitted expenses")
    def approve_selected(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                approve_expense(expense_id=obj.pk, approved_by=request.user)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Approved {done} expense(s).")


@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "supplier", "business_unit", "invoice_date", "due_date", "amount", "status")
    list_filter = ("business_unit", "status", "supplier")
    search_fields = ("invoice_number", "supplier__name")


admin.site.register(ExpenseCategory)
