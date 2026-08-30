import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.access import (
    BREAD_MANAGER, GROUP_MANAGEMENT, PRODUCTION_SUPERVISOR, SALES_OFFICER, STOREKEEPER,
    WATER_MANAGER, business_unit_for, has_any_role, role_required,
)
from commercial.models import SalesInvoice
from commercial.services import confirm_sales_invoice, record_factory_payment
from inventory.models import Item, Store
from inventory.services import get_stock_balance
from organization.models import BusinessUnit
from .forms import FactoryPaymentForm, ProductionBatchForm, ProductionMaterialUsageForm, SalesInvoiceForm, SalesInvoiceLineForm
from .models import FactoryProduct, ProductionBatch
from .services import approve_production_batch


def _factory_unit(request, code=None):
    """
    Resolve the factory business unit for the current request.

    Group Management and superusers may explicitly access any active
    BREAD/WATER business unit by code.

    Factory employees are restricted to their assigned factory.
    """

    employee_unit = business_unit_for(request.user)

    # ------------------------------------------------------------
    # GROUP MANAGEMENT / SUPERUSER
    # ------------------------------------------------------------
    # These users can explicitly select Mabinas Water (MW001)
    # or Mabinas Bread (MB001).
    if request.user.is_superuser or has_any_role(request.user, GROUP_MANAGEMENT):
        qs = BusinessUnit.objects.filter(
            unit_type__in=[
                BusinessUnit.UnitType.WATER,
                BusinessUnit.UnitType.BREAD,
            ],
            is_active=True,
        )

        if code:
            return get_object_or_404(qs, code=code)

        return qs.order_by("code").first()

    # ------------------------------------------------------------
    # FACTORY EMPLOYEE
    # ------------------------------------------------------------
    if employee_unit and employee_unit.unit_type in {
        BusinessUnit.UnitType.WATER,
        BusinessUnit.UnitType.BREAD,
    }:
        if code and code != employee_unit.code:
            raise PermissionDenied

        return employee_unit

    # ------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------
    qs = BusinessUnit.objects.filter(
        unit_type__in=[
            BusinessUnit.UnitType.WATER,
            BusinessUnit.UnitType.BREAD,
        ],
        is_active=True,
    )

    if code:
        return get_object_or_404(qs, code=code)

    return qs.order_by("code").first()

@role_required(WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, STOREKEEPER, SALES_OFFICER, GROUP_MANAGEMENT)
def factory_dashboard(request, code=None):
    unit = _factory_unit(request, code)
    if not unit:
        messages.warning(request, "No active factory business unit is configured.")
        return redirect("home")
    today = timezone.localdate()
    batches = ProductionBatch.objects.filter(business_unit=unit, production_date=today).select_related("product", "supervisor")
    invoices = SalesInvoice.objects.filter(business_unit=unit, invoice_date=today).select_related("customer")
    products = FactoryProduct.objects.filter(business_unit=unit, is_active=True).select_related("inventory_item")
    stores = list(Store.objects.filter(business_unit=unit, is_active=True))
    low_stock = []
    for product in products:
        balance = sum((get_stock_balance(store=store, item=product.inventory_item) for store in stores), start=product.minimum_stock * 0)
        if balance <= product.minimum_stock:
            low_stock.append((product, balance))
    return render(request, "factory/dashboard.html", {
        "unit": unit,
        "batches": batches,
        "invoices": invoices,
        "production_planned": batches.aggregate(v=Sum("planned_quantity"))["v"] or 0,
        "production_accepted": batches.aggregate(v=Sum("accepted_quantity"))["v"] or 0,
        "sales_count": invoices.exclude(status=SalesInvoice.Status.CANCELLED).count(),
        "low_stock": low_stock[:10],
    })


@role_required(WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, GROUP_MANAGEMENT)
def batch_list(request, code):
    unit = _factory_unit(request, code)
    batches = ProductionBatch.objects.filter(business_unit=unit).select_related("product", "supervisor").order_by("-production_date", "-created_at")[:250]
    return render(request, "factory/batch_list.html", {"unit": unit, "batches": batches})


@role_required(WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, GROUP_MANAGEMENT)
def batch_create(request, code):
    unit = _factory_unit(request, code)
    form = ProductionBatchForm(request.POST or None, business_unit=unit)
    if request.method == "POST" and form.is_valid():
        batch = form.save()
        messages.success(request, f"Production batch {batch.batch_number} created.")
        return redirect("factory:batch_detail", code=unit.code, pk=batch.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"New {unit.name} Production Batch", "cancel_url": f"/factory/{unit.code}/batches/"})


@role_required(WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, GROUP_MANAGEMENT)
def batch_detail(request, code, pk):
    unit = _factory_unit(request, code)
    batch = get_object_or_404(ProductionBatch.objects.select_related("product", "recipe", "raw_material_store", "finished_goods_store", "supervisor"), pk=pk, business_unit=unit)
    return render(request, "factory/batch_detail.html", {"unit": unit, "batch": batch, "usages": batch.material_usages.select_related("item")})


@role_required(WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, GROUP_MANAGEMENT)
def batch_add_material(request, code, pk):
    unit = _factory_unit(request, code)
    batch = get_object_or_404(ProductionBatch, pk=pk, business_unit=unit)
    form = ProductionMaterialUsageForm(request.POST or None, batch=batch)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production material added.")
        return redirect("factory:batch_detail", code=unit.code, pk=batch.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Add Material - {batch.batch_number}", "cancel_url": f"/factory/{unit.code}/batches/{batch.pk}/"})


@role_required(WATER_MANAGER, BREAD_MANAGER, GROUP_MANAGEMENT)
def batch_approve(request, code, pk):
    unit = _factory_unit(request, code)
    batch = get_object_or_404(ProductionBatch, pk=pk, business_unit=unit)
    if request.method == "POST":
        try:
            approve_production_batch(batch_id=batch.pk, approved_by=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Production approved and stock movements posted.")
    return redirect("factory:batch_detail", code=unit.code, pk=batch.pk)


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_list(request, code):
    unit = _factory_unit(request, code)
    invoices = SalesInvoice.objects.filter(business_unit=unit).select_related("customer", "salesperson").order_by("-invoice_date", "-created_at")[:250]
    return render(request, "factory/sales_list.html", {"unit": unit, "invoices": invoices})


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_create(request, code):
    unit = _factory_unit(request, code)
    form = SalesInvoiceForm(request.POST or None, business_unit=unit, user=request.user)
    if request.method == "POST" and form.is_valid():
        invoice = form.save()
        messages.success(request, f"Invoice {invoice.invoice_number} created. Add product lines before confirmation.")
        return redirect("factory:sales_detail", code=unit.code, pk=invoice.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"New {unit.name} Sale", "cancel_url": f"/factory/{unit.code}/sales/"})


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_detail(request, code, pk):
    unit = _factory_unit(request, code)
    invoice = get_object_or_404(SalesInvoice.objects.select_related("customer", "fulfillment_store", "salesperson"), pk=pk, business_unit=unit)
    return render(request, "factory/sales_detail.html", {"unit": unit, "invoice": invoice, "lines": invoice.lines.select_related("product"), "payments": invoice.payments.all()})


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_add_line(request, code, pk):
    unit = _factory_unit(request, code)
    invoice = get_object_or_404(SalesInvoice, pk=pk, business_unit=unit, status=SalesInvoice.Status.DRAFT)
    form = SalesInvoiceLineForm(request.POST or None, invoice=invoice)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product added to invoice.")
        return redirect("factory:sales_detail", code=unit.code, pk=invoice.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Add Product - {invoice.invoice_number}", "cancel_url": f"/factory/{unit.code}/sales/{invoice.pk}/"})


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_confirm(request, code, pk):
    unit = _factory_unit(request, code)
    invoice = get_object_or_404(SalesInvoice, pk=pk, business_unit=unit)
    if request.method == "POST":
        try:
            confirm_sales_invoice(invoice_id=invoice.pk, confirmed_by=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Sale confirmed and finished-goods stock reduced.")
    return redirect("factory:sales_detail", code=unit.code, pk=invoice.pk)


@role_required(WATER_MANAGER, BREAD_MANAGER, SALES_OFFICER, GROUP_MANAGEMENT)
def sales_payment(request, code, pk):
    unit = _factory_unit(request, code)
    invoice = get_object_or_404(SalesInvoice, pk=pk, business_unit=unit)
    form = FactoryPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            record_factory_payment(
                invoice_id=invoice.pk,
                reference=f"FPT-{uuid.uuid4().hex[:12].upper()}",
                received_by=request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Customer payment recorded.")
            return redirect("factory:sales_detail", code=unit.code, pk=invoice.pk)
    return render(request, "layouts/form_page.html", {"form": form, "title": f"Receive Payment - {invoice.invoice_number}", "cancel_url": f"/factory/{unit.code}/sales/{invoice.pk}/"})
