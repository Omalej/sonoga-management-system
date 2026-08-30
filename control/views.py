from django.db.models import Q
from django.shortcuts import render
from accounts.access import (
    ACCOUNTANT, AUDITOR, BREAD_MANAGER, GROUP_MANAGEMENT, HOTEL_MANAGER,
    HR_MANAGER, STOREKEEPER, WATER_MANAGER, business_unit_for, has_any_role, role_required,
)
from finance.models import Expense
from procurement.models import PurchaseRequest
from payroll.models import PayrollRun
from inventory.models import Item, Store
from inventory.services import get_stock_balance
from hotel.models import HousekeepingTask, MaintenanceTicket
from .models import ApprovalRequest, AuditLog



@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HR_MANAGER, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
def control_dashboard(request):
    return render(request, "control/dashboard.html", {
        "pending_approvals": ApprovalRequest.objects.filter(
            status=ApprovalRequest.Status.PENDING
        ).count(),
        "audit_events": AuditLog.objects.count(),
    })
@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HR_MANAGER, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER)
def approval_center(request):
    unit = business_unit_for(request.user)
    expenses = Expense.objects.filter(status=Expense.Status.SUBMITTED).select_related("business_unit", "department", "category", "requested_by")
    purchase_requests = PurchaseRequest.objects.filter(status=PurchaseRequest.Status.SUBMITTED).select_related("business_unit", "department", "requested_by")
    payrolls = PayrollRun.objects.filter(status=PayrollRun.Status.GENERATED).select_related("business_unit", "created_by")
    generic = ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING).select_related("business_unit", "requested_by", "assigned_to")
    if unit and not (request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT)):
        expenses = expenses.filter(business_unit=unit)
        purchase_requests = purchase_requests.filter(business_unit=unit)
        payrolls = payrolls.filter(business_unit=unit)
        generic = generic.filter(Q(business_unit=unit) | Q(business_unit__isnull=True))
    return render(request, "control/approvals.html", {
        "expenses": expenses[:100], "purchase_requests": purchase_requests[:100],
        "payrolls": payrolls[:100], "generic": generic[:100],
        "total_pending": expenses.count() + purchase_requests.count() + payrolls.count() + generic.count(),
    })


@role_required(GROUP_MANAGEMENT, AUDITOR)
def audit_log(request):
    qs = AuditLog.objects.select_related("actor", "business_unit")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(reference_number__icontains=q) | Q(module__icontains=q) | Q(action__icontains=q))
    return render(request, "control/audit_log.html", {"events": qs[:500], "q": q})


@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HR_MANAGER, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
def notifications(request):
    unit = business_unit_for(request.user)
    alerts = []
    units_filter = [unit] if unit and not (request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT)) else None

    if request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER):
        expenses = Expense.objects.filter(status=Expense.Status.SUBMITTED)
        prs = PurchaseRequest.objects.filter(status=PurchaseRequest.Status.SUBMITTED)
        if units_filter:
            expenses = expenses.filter(business_unit=unit); prs = prs.filter(business_unit=unit)
        if expenses.exists(): alerts.append({"level": "warning", "title": "Expenses awaiting approval", "detail": f"{expenses.count()} submitted expense(s) need review.", "url": "/control/approvals/"})
        if prs.exists(): alerts.append({"level": "warning", "title": "Purchase requests awaiting approval", "detail": f"{prs.count()} purchase request(s) need review.", "url": "/control/approvals/"})

    if request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT, HR_MANAGER, ACCOUNTANT):
        payrolls = PayrollRun.objects.filter(status=PayrollRun.Status.GENERATED)
        if units_filter: payrolls = payrolls.filter(business_unit=unit)
        if payrolls.exists(): alerts.append({"level": "warning", "title": "Payroll awaiting approval", "detail": f"{payrolls.count()} generated payroll run(s) need action.", "url": "/payroll/"})

    if request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT, HOTEL_MANAGER):
        housekeeping = HousekeepingTask.objects.exclude(status__in=[HousekeepingTask.Status.VERIFIED])
        maintenance = MaintenanceTicket.objects.exclude(status__in=[MaintenanceTicket.Status.VERIFIED, MaintenanceTicket.Status.CANCELLED])
        if housekeeping.exists(): alerts.append({"level": "info", "title": "Housekeeping work open", "detail": f"{housekeeping.count()} housekeeping task(s) remain open.", "url": "/hotel/housekeeping/"})
        if maintenance.exists(): alerts.append({"level": "warning", "title": "Maintenance work open", "detail": f"{maintenance.count()} maintenance request(s) remain open.", "url": "/hotel/"})

    if request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER):
        stores = Store.objects.filter(is_active=True)
        items = Item.objects.filter(is_active=True, reorder_level__gt=0)
        if units_filter:
            stores = stores.filter(business_unit=unit); items = items.filter(business_unit=unit)
        low = []
        for item in items:
            unit_stores = stores.filter(business_unit=item.business_unit)
            balance = sum((get_stock_balance(store=store, item=item) for store in unit_stores), 0)
            if balance <= item.reorder_level:
                low.append((item.business_unit, item, balance))
        if low:
            alerts.append({"level": "danger", "title": "Low stock", "detail": f"{len(low)} store/item balance(s) are at or below reorder level.", "url": "/inventory/"})

    return render(request, "control/notifications.html", {"alerts": alerts})
