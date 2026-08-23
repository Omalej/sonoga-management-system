from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseOrder, PurchaseOrderLine, GoodsReceipt, GoodsReceiptLine
from .services import approve_purchase_request, post_goods_receipt


class PurchaseRequestLineInline(admin.TabularInline):
    model = PurchaseRequestLine
    extra = 1


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "business_unit", "department", "status", "required_date", "created_at")
    list_filter = ("business_unit", "department", "status")
    search_fields = ("request_number", "reason")
    inlines = [PurchaseRequestLineInline]
    actions = ["approve_selected"]

    @admin.action(description="Approve selected submitted purchase requests")
    def approve_selected(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                approve_purchase_request(request_id=obj.pk, approved_by=request.user)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Approved {done} purchase request(s).")


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "business_unit", "supplier", "order_date", "status")
    list_filter = ("business_unit", "status", "supplier")
    search_fields = ("order_number", "supplier__name")
    inlines = [PurchaseOrderLineInline]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 1


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "purchase_order", "destination_store", "received_date", "status")
    list_filter = ("status", "destination_store__business_unit")
    search_fields = ("receipt_number", "purchase_order__order_number")
    inlines = [GoodsReceiptLineInline]
    actions = ["post_to_stock"]

    @admin.action(description="Post selected goods receipts to inventory")
    def post_to_stock(self, request, queryset):
        done = 0
        for obj in queryset:
            try:
                post_goods_receipt(receipt_id=obj.pk, posted_by=request.user)
                done += 1
            except ValidationError as exc:
                self.message_user(request, f"{obj}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Posted {done} goods receipt(s) to stock.")


admin.site.register(Supplier)
