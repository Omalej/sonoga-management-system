from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from control.services import log_event
from .models import Expense, ExpensePayment


@transaction.atomic
def approve_expense(*, expense_id: int, approved_by) -> Expense:
    expense = Expense.objects.select_for_update().get(pk=expense_id)
    if expense.status == Expense.Status.APPROVED:
        return expense
    if expense.status != Expense.Status.SUBMITTED:
        raise ValidationError("Only submitted expenses can be approved.")
    expense.status = Expense.Status.APPROVED
    expense.approved_by = approved_by
    expense.approved_at = timezone.now()
    expense.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    log_event(actor=approved_by, business_unit=expense.business_unit, module="finance", action="expense_approve", description=f"Approved expense {expense.expense_number}.", reference_type="Expense", reference_id=expense.pk, reference_number=expense.expense_number, new_values={"amount": str(expense.amount)})
    return expense


@transaction.atomic
def record_expense_payment(*, expense_id: int, reference: str, payment_date, amount, method: str, paid_by, external_reference="", notes="") -> ExpensePayment:
    expense = Expense.objects.select_for_update().get(pk=expense_id)
    if expense.status not in {Expense.Status.APPROVED, Expense.Status.PARTIALLY_PAID}:
        raise ValidationError("Only approved expenses can be paid.")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")
    if amount > expense.balance:
        raise ValidationError(f"Payment exceeds expense balance of {expense.balance}.")

    payment = ExpensePayment(
        expense=expense,
        reference=reference,
        payment_date=payment_date,
        amount=amount,
        method=method,
        paid_by=paid_by,
        external_reference=external_reference,
        notes=notes,
    )
    payment.full_clean()
    payment.save()

    expense.refresh_from_db()
    expense.status = Expense.Status.PAID if expense.balance == 0 else Expense.Status.PARTIALLY_PAID
    expense.save(update_fields=["status", "updated_at"])
    log_event(actor=paid_by, business_unit=expense.business_unit, module="finance", action="expense_payment", description=f"Recorded payment {payment.reference} for expense {expense.expense_number}.", reference_type="ExpensePayment", reference_id=payment.pk, reference_number=payment.reference, new_values={"amount": str(payment.amount)})
    return payment
