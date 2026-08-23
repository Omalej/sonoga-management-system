from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .services import confirm_sales_invoice
from .models import (
    Customer, SalesInvoice, SalesInvoiceLine, FactoryPayment,
    DistributionRoute, Vehicle, Delivery, DeliveryLine, ProductReturn,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_number", "name", "customer_type", "phone", "credit_limit", "is_active")
    list_filter = ("customer_type", "business_units", "is_active")
    search_fields = ("customer_number", "name", "phone", "email")
    filter_horizontal = ("business_units",)


class SalesInvoiceLineInline(admin.TabularInline):
    model = SalesInvoiceLine
    extra = 1


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "business_unit", "customer", "invoice_date", "net_total", "payments_total", "balance", "status")
    list_filter = ("business_unit", "status", "invoice_date")
    search_fields = ("invoice_number", "customer__name", "customer__phone")
    date_hierarchy = "invoice_date"
    inlines = [SalesInvoiceLineInline]
    actions = ["confirm_selected_invoices"]

    @admin.action(description="Confirm selected invoices and deduct stock")
    def confirm_selected_invoices(self, request, queryset):
        confirmed = 0
        for invoice in queryset:
            try:
                confirm_sales_invoice(invoice_id=invoice.pk, confirmed_by=request.user)
                confirmed += 1
            except ValidationError as exc:
                self.message_user(request, f"{invoice.invoice_number}: {exc}", level=messages.ERROR)
        if confirmed:
            self.message_user(request, f"Confirmed {confirmed} invoice(s).", level=messages.SUCCESS)


@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "product", "quantity", "unit_price", "discount_amount", "line_total")
    list_filter = ("invoice__business_unit",)
    search_fields = ("invoice__invoice_number", "product__name")


@admin.register(FactoryPayment)
class FactoryPaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "invoice", "amount", "method", "status", "received_by", "created_at")
    list_filter = ("invoice__business_unit", "method", "status")
    search_fields = ("reference", "external_reference", "invoice__invoice_number", "invoice__customer__name")


@admin.register(DistributionRoute)
class DistributionRouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "business_unit", "vehicle_type", "driver", "status")
    list_filter = ("business_unit", "status")
    search_fields = ("registration_number", "vehicle_type")


class DeliveryLineInline(admin.TabularInline):
    model = DeliveryLine
    extra = 1


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("delivery_number", "business_unit", "customer", "route", "vehicle", "driver", "status", "expected_amount", "collected_amount")
    list_filter = ("business_unit", "route", "status")
    search_fields = ("delivery_number", "customer__name", "vehicle__registration_number")
    inlines = [DeliveryLineInline]


@admin.register(DeliveryLine)
class DeliveryLineAdmin(admin.ModelAdmin):
    list_display = ("delivery", "product", "quantity_loaded", "quantity_delivered", "quantity_returned", "quantity_damaged")
    list_filter = ("delivery__business_unit",)
    search_fields = ("delivery__delivery_number", "product__name")


@admin.register(ProductReturn)
class ProductReturnAdmin(admin.ModelAdmin):
    list_display = ("return_number", "business_unit", "customer", "product", "quantity", "resolution", "created_at")
    list_filter = ("business_unit", "resolution")
    search_fields = ("return_number", "customer__name", "product__name", "reason")
