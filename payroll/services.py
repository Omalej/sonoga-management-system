from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from hr.models import Employee
from .models import PayrollLine, PayrollRun


@transaction.atomic
def generate_payroll(*, payroll_run_id: int) -> PayrollRun:
    run = PayrollRun.objects.select_for_update().get(pk=payroll_run_id)
    if run.status not in {PayrollRun.Status.DRAFT, PayrollRun.Status.GENERATED}:
        raise ValidationError("Only draft/generated payroll runs can be generated.")

    employees = Employee.objects.filter(business_unit=run.business_unit, status=Employee.Status.ACTIVE)
    for employee in employees:
        line, created = PayrollLine.objects.get_or_create(
            payroll_run=run,
            employee=employee,
            defaults={"basic_salary": employee.basic_salary},
        )
        if created:
            line.save()

    run.status = PayrollRun.Status.GENERATED
    run.save(update_fields=["status", "updated_at"])
    return run


@transaction.atomic
def approve_payroll(*, payroll_run_id: int, approved_by) -> PayrollRun:
    run = PayrollRun.objects.select_for_update().get(pk=payroll_run_id)
    if run.status == PayrollRun.Status.APPROVED:
        return run
    if run.status != PayrollRun.Status.GENERATED:
        raise ValidationError("Only generated payroll can be approved.")
    if not run.lines.exists():
        raise ValidationError("Payroll has no employee lines.")
    run.status = PayrollRun.Status.APPROVED
    run.approved_by = approved_by
    run.approved_at = timezone.now()
    run.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return run


@transaction.atomic
def mark_payroll_paid(*, payroll_run_id: int) -> PayrollRun:
    run = PayrollRun.objects.select_for_update().get(pk=payroll_run_id)
    if run.status != PayrollRun.Status.APPROVED:
        raise ValidationError("Only approved payroll can be marked paid.")
    run.lines.update(is_paid=True)
    run.status = PayrollRun.Status.PAID
    run.paid_at = timezone.now()
    run.save(update_fields=["status", "paid_at", "updated_at"])
    return run
