from django.conf import settings
from django.db import models
from core.models import TimeStampedModel
from organization.models import BusinessUnit


class ApprovalRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED = "RETURNED", "Returned for Correction"
        CANCELLED = "CANCELLED", "Cancelled"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="approval_requests")
    module = models.CharField(max_length=50, db_index=True)
    reference_type = models.CharField(max_length=80)
    reference_id = models.CharField(max_length=80, db_index=True)
    reference_number = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approval_requests_created")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests_assigned")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    decision_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests_decided")
    decision_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "module", "created_at"])]

    def __str__(self):
        return f"{self.module} - {self.reference_number or self.reference_id}"


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    module = models.CharField(max_length=50, db_index=True)
    action = models.CharField(max_length=50, db_index=True)
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=80, blank=True, db_index=True)
    reference_number = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["module", "action", "created_at"])]

    def __str__(self):
        return f"{self.module}:{self.action} - {self.reference_number or self.reference_id}"
