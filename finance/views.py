import uuid
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.access import ACCOUNTANT, GROUP_MANAGEMENT, role_required
from .forms import ExpenseForm, ExpensePaymentForm
from .models import Expense, ExpensePayment
from .services import approve_expense, record_expense_payment


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def finance_dashboard(request):
    today = timezone.localdate()
    expenses = Expense.objects.filter(expense_date=today)
    context = {
        "today": today,
        "expense_total": expenses.exclude(status__in=[Expense.Status.REJECTED, Expense.Status.CANCELLED]).aggregate(v=Sum("amount"))["v"] or 0,
        "pending": Expense.objects.filter(status=Expense.Status.SUBMITTED).select_related("business_unit", "department", "category", "requested_by")[:20],
        "recent": Expense.objects.select_related("business_unit", "category").order_by("-expense_date", "-created_at")[:20],
    }
    return render(request, "finance/dashboard.html", context)


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def expense_list(request):
    expenses = Expense.objects.select_related("business_unit", "department", "category", "requested_by", "approved_by").order_by("-expense_date", "-created_at")[:300]
    return render(request, "finance/expense_list.html", {"expenses": expenses})


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def expense_create(request):
    form = ExpenseForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        expense = form.save()
        messages.success(request, f"Expense {expense.expense_number} submitted.")
        return redirect("finance:expense_detail", pk=expense.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "Record Expense", "cancel_url": "/finance/expenses/"})


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def expense_detail(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("business_unit", "department", "category", "supplier", "requested_by", "approved_by"), pk=pk)
    return render(request, "finance/expense_detail.html", {"expense": expense, "payments": expense.payments.all()})


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def expense_approve(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == "POST":
        try:
            approve_expense(expense_id=expense.pk, approved_by=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Expense approved.")
    return redirect("finance:expense_detail", pk=pk)


@role_required(ACCOUNTANT, GROUP_MANAGEMENT)
def expense_payment(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    form = ExpensePaymentForm(request.POST or None, initial={"payment_date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        try:
            record_expense_payment(
                expense_id=expense.pk,
                reference=f"EPT-{uuid.uuid4().hex[:12].upper()}",
                paid_by=request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Expense payment recorded.")
            return redirect("finance:expense_detail", pk=pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Pay Expense {expense.expense_number}", "cancel_url": f"/finance/expenses/{pk}/"})
