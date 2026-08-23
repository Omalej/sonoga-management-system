from django.contrib import admin
from .models import ApprovalRequest, AuditLog


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("module", "reference_number", "business_unit", "amount", "status", "requested_by", "created_at")
    list_filter = ("module", "business_unit", "status")
    search_fields = ("reference_number", "reference_id", "reason")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "module", "action", "business_unit", "reference_number")
    list_filter = ("module", "action", "business_unit")
    search_fields = ("description", "reference_number", "reference_id")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
