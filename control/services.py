from django.db import transaction
from django.utils import timezone
from .models import ApprovalRequest, AuditLog


def log_event(*, actor, module, action, description, business_unit=None, reference_type="", reference_id="", reference_number="", old_values=None, new_values=None, ip_address=None):
    return AuditLog.objects.create(
        actor=actor,
        business_unit=business_unit,
        module=module,
        action=action,
        description=description,
        reference_type=reference_type,
        reference_id=str(reference_id or ""),
        reference_number=reference_number,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
    )


@transaction.atomic
def decide_approval(*, approval_id: int, decision: str, decided_by, reason="") -> ApprovalRequest:
    approval = ApprovalRequest.objects.select_for_update().get(pk=approval_id)
    if approval.status != ApprovalRequest.Status.PENDING:
        return approval
    allowed = {ApprovalRequest.Status.APPROVED, ApprovalRequest.Status.REJECTED, ApprovalRequest.Status.RETURNED}
    if decision not in allowed:
        raise ValueError("Unsupported approval decision.")
    approval.status = decision
    approval.decision_by = decided_by
    approval.decision_at = timezone.now()
    approval.reason = reason
    approval.save(update_fields=["status", "decision_by", "decision_at", "reason", "updated_at"])
    return approval
