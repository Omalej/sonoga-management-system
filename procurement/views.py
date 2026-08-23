from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.access import ACCOUNTANT, BREAD_MANAGER, GROUP_MANAGEMENT, HOTEL_MANAGER, STOREKEEPER, WATER_MANAGER, business_unit_for, role_required
from control.services import log_event
from organization.models import BusinessUnit
from .forms import GoodsReceiptForm, GoodsReceiptLineForm, PurchaseOrderForm, PurchaseOrderLineForm, PurchaseRequestForm, PurchaseRequestLineForm
from .models import GoodsReceipt, PurchaseOrder, PurchaseRequest
from .services import approve_purchase_request, post_goods_receipt

ROLES = (GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)


def _units_for(user):
    if user.is_superuser or user.groups.filter(name=GROUP_MANAGEMENT).exists():
        return BusinessUnit.objects.filter(is_active=True)
    unit = business_unit_for(user)
    return BusinessUnit.objects.filter(pk=unit.pk) if unit else BusinessUnit.objects.none()


@role_required(*ROLES)
def dashboard(request):
    units = _units_for(request.user)
    prs = PurchaseRequest.objects.filter(business_unit__in=units).select_related("business_unit", "department", "requested_by")
    pos = PurchaseOrder.objects.filter(business_unit__in=units).select_related("business_unit", "supplier")
    receipts = GoodsReceipt.objects.filter(purchase_order__business_unit__in=units).select_related("purchase_order", "destination_store")
    return render(request, "procurement/dashboard.html", {
        "pending_pr": prs.filter(status=PurchaseRequest.Status.SUBMITTED)[:20],
        "recent_pr": prs[:20], "recent_po": pos.order_by("-created_at")[:20], "recent_receipts": receipts.order_by("-created_at")[:20],
    })


@role_required(*ROLES)
def request_create(request):
    form = PurchaseRequestForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        pr = form.save(); messages.success(request, "Purchase request created. Add items before submitting.")
        return redirect("procurement:request_detail", pk=pr.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "New Purchase Request", "cancel_url": "/procurement/"})


@role_required(*ROLES)
def request_detail(request, pk):
    pr = get_object_or_404(PurchaseRequest.objects.filter(business_unit__in=_units_for(request.user)).select_related("business_unit", "department", "requested_by", "approved_by"), pk=pk)
    form = PurchaseRequestLineForm(request.POST or None, purchase_request=pr)
    if request.method == "POST" and "add_line" in request.POST and pr.status == PurchaseRequest.Status.DRAFT and form.is_valid():
        form.save(); messages.success(request, "Item added."); return redirect("procurement:request_detail", pk=pk)
    return render(request, "procurement/request_detail.html", {"pr": pr, "line_form": form})


@role_required(*ROLES)
def request_submit(request, pk):
    pr = get_object_or_404(PurchaseRequest.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        if pr.status != PurchaseRequest.Status.DRAFT:
            messages.error(request, "Only draft requests can be submitted.")
        elif not pr.lines.exists():
            messages.error(request, "Add at least one item before submission.")
        else:
            pr.status = PurchaseRequest.Status.SUBMITTED; pr.save(update_fields=["status", "updated_at"])
            log_event(actor=request.user, business_unit=pr.business_unit, module="procurement", action="SUBMIT", description=f"Submitted purchase request {pr.request_number}", reference_type="PurchaseRequest", reference_id=pr.pk, reference_number=pr.request_number)
            messages.success(request, "Purchase request submitted for approval.")
    return redirect("procurement:request_detail", pk=pk)


@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER)
def request_approve(request, pk):
    get_object_or_404(PurchaseRequest.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        try:
            pr = approve_purchase_request(request_id=pk, approved_by=request.user)
            log_event(actor=request.user, business_unit=pr.business_unit, module="procurement", action="APPROVE", description=f"Approved purchase request {pr.request_number}", reference_type="PurchaseRequest", reference_id=pr.pk, reference_number=pr.request_number)
            messages.success(request, "Purchase request approved.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("procurement:request_detail", pk=pk)


@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER)
def order_create(request):
    form = PurchaseOrderForm(request.POST or None, user=request.user, initial={"order_date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        po = form.save()
        if po.request_id:
            for line in po.request.lines.select_related("item"):
                po.lines.create(item=line.item, quantity=line.quantity, unit_cost=line.estimated_unit_cost)
            po.request.status = PurchaseRequest.Status.ORDERED; po.request.save(update_fields=["status", "updated_at"])
        messages.success(request, "Purchase order created.")
        return redirect("procurement:order_detail", pk=po.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "New Purchase Order", "cancel_url": "/procurement/"})


@role_required(*ROLES)
def order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.filter(business_unit__in=_units_for(request.user)).select_related("business_unit", "supplier", "request", "created_by"), pk=pk)
    form = PurchaseOrderLineForm(request.POST or None, order=po)
    if request.method == "POST" and "add_line" in request.POST and po.status == PurchaseOrder.Status.DRAFT and form.is_valid():
        form.save(); messages.success(request, "Order item added."); return redirect("procurement:order_detail", pk=pk)
    return render(request, "procurement/order_detail.html", {"po": po, "line_form": form})


@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER)
def order_issue(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.filter(business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        if po.status != PurchaseOrder.Status.DRAFT or not po.lines.exists():
            messages.error(request, "Only a draft order with items can be issued.")
        else:
            po.status = PurchaseOrder.Status.ISSUED; po.approved_by = request.user; po.save(update_fields=["status", "approved_by", "updated_at"])
            messages.success(request, "Purchase order issued.")
    return redirect("procurement:order_detail", pk=pk)


@role_required(*ROLES)
def receipt_create(request):
    form = GoodsReceiptForm(request.POST or None, user=request.user, initial={"received_date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        grn = form.save(); messages.success(request, "Goods receipt created. Record delivered quantities.")
        return redirect("procurement:receipt_detail", pk=grn.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": "Receive Goods", "cancel_url": "/procurement/"})


@role_required(*ROLES)
def receipt_detail(request, pk):
    grn = get_object_or_404(GoodsReceipt.objects.filter(purchase_order__business_unit__in=_units_for(request.user)).select_related("purchase_order", "destination_store", "received_by", "posted_by"), pk=pk)
    form = GoodsReceiptLineForm(request.POST or None, receipt=grn)
    if request.method == "POST" and "add_line" in request.POST and grn.status == GoodsReceipt.Status.DRAFT and form.is_valid():
        form.save(); messages.success(request, "Receipt line added."); return redirect("procurement:receipt_detail", pk=pk)
    return render(request, "procurement/receipt_detail.html", {"grn": grn, "line_form": form})


@role_required(GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
def receipt_post(request, pk):
    get_object_or_404(GoodsReceipt.objects.filter(purchase_order__business_unit__in=_units_for(request.user)), pk=pk)
    if request.method == "POST":
        try:
            grn = post_goods_receipt(receipt_id=pk, posted_by=request.user)
            log_event(actor=request.user, business_unit=grn.purchase_order.business_unit, module="procurement", action="POST_RECEIPT", description=f"Posted goods receipt {grn.receipt_number}", reference_type="GoodsReceipt", reference_id=grn.pk, reference_number=grn.receipt_number)
            messages.success(request, "Goods receipt posted to inventory.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("procurement:receipt_detail", pk=pk)
