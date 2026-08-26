from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from accounts.access import GROUP_MANAGEMENT, HR_MANAGER, ACCOUNTANT, business_unit_for, role_required
from organization.models import BusinessUnit
from control.services import log_event
from .forms import PayrollLineEditForm, PayrollRunForm
from .models import PayrollLine, PayrollRun
from .services import approve_payroll, generate_payroll, mark_payroll_paid

ROLES = (GROUP_MANAGEMENT, HR_MANAGER, ACCOUNTANT)


def _units_for(user):
    if user.is_superuser or user.groups.filter(name=GROUP_MANAGEMENT).exists():
        return BusinessUnit.objects.filter(is_active=True)
    unit = business_unit_for(user)
    return BusinessUnit.objects.filter(pk=unit.pk) if unit else BusinessUnit.objects.none()


@role_required(*ROLES)
def payroll_list(request):
    runs = PayrollRun.objects.filter(business_unit__in=_units_for(request.user)).select_related("business_unit", "created_by", "approved_by")[:200]
    return render(request, "payroll/payroll_list.html", {"runs": runs})


@role_required(GROUP_MANAGEMENT, HR_MANAGER)
def payroll_create(request):
    form = PayrollRunForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        run = form.save(); messages.success(request, "Payroll run created. Generate employee lines next.")
        return redirect("payroll:detail", pk=run.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "New Payroll Run", "cancel_url": "/payroll/"})


@role_required(*ROLES)
def payroll_detail(request, pk):
    run = get_object_or_404(PayrollRun.objects.filter(business_unit__in=_units_for(request.user)).select_related("business_unit", "created_by", "approved_by").prefetch_related("lines__employee"), pk=pk)
    return render(request, "payroll/payroll_detail.html", {"run": run})


@role_required(GROUP_MANAGEMENT, HR_MANAGER)
def payroll_generate(request, pk):
    get_object_or_404(PayrollRun.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        try:
            run = generate_payroll(payroll_run_id=pk)
            log_event(actor=request.user, business_unit=run.business_unit, module="payroll", action="GENERATE", description=f"Generated payroll {run.payroll_number}", reference_type="PayrollRun", reference_id=run.pk, reference_number=run.payroll_number)
            messages.success(request, "Payroll lines generated from active employees.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("payroll:detail", pk=pk)


@role_required(GROUP_MANAGEMENT, HR_MANAGER)
def payroll_line_edit(request, pk, line_id):
    run = get_object_or_404(PayrollRun.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    line = get_object_or_404(PayrollLine, pk=line_id, payroll_run=run)
    if run.status not in {PayrollRun.Status.DRAFT, PayrollRun.Status.GENERATED}:
        messages.error(request, "Approved payroll lines cannot be edited.")
        return redirect("payroll:detail", pk=pk)
    form = PayrollLineEditForm(request.POST or None, instance=line)
    if request.method == "POST" and form.is_valid():
        form.save(); messages.success(request, "Payroll line updated.")
        return redirect("payroll:detail", pk=pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Edit Payroll · {line.employee.full_name}", "cancel_url": f"/payroll/{pk}/"})


@role_required(GROUP_MANAGEMENT, HR_MANAGER)
def payroll_approve(request, pk):
    get_object_or_404(PayrollRun.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        try:
            run = approve_payroll(payroll_run_id=pk, approved_by=request.user)
            log_event(actor=request.user, business_unit=run.business_unit, module="payroll", action="APPROVE", description=f"Approved payroll {run.payroll_number}", reference_type="PayrollRun", reference_id=run.pk, reference_number=run.payroll_number)
            messages.success(request, "Payroll approved.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("payroll:detail", pk=pk)


@role_required(GROUP_MANAGEMENT, ACCOUNTANT)
def payroll_paid(request, pk):
    get_object_or_404(PayrollRun.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        try:
            run = mark_payroll_paid(payroll_run_id=pk)
            log_event(actor=request.user, business_unit=run.business_unit, module="payroll", action="PAID", description=f"Marked payroll {run.payroll_number} paid", reference_type="PayrollRun", reference_id=run.pk, reference_number=run.payroll_number)
            messages.success(request, "Payroll marked paid.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("payroll:detail", pk=pk)
