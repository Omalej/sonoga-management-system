import uuid
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render
from accounts.access import (
    BREAD_MANAGER, GROUP_MANAGEMENT, HOTEL_MANAGER, STOREKEEPER, WATER_MANAGER,
    business_unit_for, role_required,
)
from organization.models import BusinessUnit
from .forms import StockAdjustmentForm, StockTransferForm
from .models import Item, Store, StockMovement
from .services import get_stock_balance, post_stock_movement, transfer_stock

ROLES = (GROUP_MANAGEMENT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)


def _units_for(user):
    if user.is_superuser or user.groups.filter(name=GROUP_MANAGEMENT).exists():
        return BusinessUnit.objects.filter(is_active=True)
    unit = business_unit_for(user)
    return BusinessUnit.objects.filter(pk=unit.pk) if unit else BusinessUnit.objects.none()


@role_required(*ROLES)
def inventory_dashboard(request):
    units = _units_for(request.user)
    stores = Store.objects.filter(business_unit__in=units, is_active=True).select_related("business_unit")
    items = Item.objects.filter(business_unit__in=units, is_active=True).select_related("business_unit")
    low_stock = []
    balances = []
    for store in stores:
        for item in items.filter(business_unit=store.business_unit):
            balance = get_stock_balance(store=store, item=item)
            if balance != 0:
                balances.append((store, item, balance))
    for item in items.filter(reorder_level__gt=0):
        unit_stores = stores.filter(business_unit=item.business_unit)
        total_balance = sum((get_stock_balance(store=store, item=item) for store in unit_stores), 0)
        if total_balance <= item.reorder_level:
            low_stock.append((item.business_unit, item, total_balance))
    recent = StockMovement.objects.filter(store__business_unit__in=units).select_related("store", "item", "posted_by")[:30]
    return render(request, "inventory/dashboard.html", {
        "stores": stores, "items_count": items.count(), "balances": balances[:100],
        "low_stock": low_stock[:50], "recent": recent,
    })


@role_required(*ROLES)
def movement_list(request):
    units = _units_for(request.user)
    qs = StockMovement.objects.filter(store__business_unit__in=units).select_related("store", "item", "posted_by")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(item__name__icontains=q) | Q(reference__icontains=q) | Q(store__name__icontains=q))
    return render(request, "inventory/movement_list.html", {"movements": qs[:500], "q": q})


@role_required(GROUP_MANAGEMENT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
def stock_adjustment(request):
    form = StockAdjustmentForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        direction = StockMovement.Direction.IN if data["adjustment"] == "IN" else StockMovement.Direction.OUT
        movement_type = StockMovement.MovementType.ADJUSTMENT_IN if direction == StockMovement.Direction.IN else StockMovement.MovementType.ADJUSTMENT_OUT
        try:
            post_stock_movement(
                store=data["store"], item=data["item"], direction=direction,
                movement_type=movement_type, quantity=data["quantity"], posted_by=request.user,
                unit_cost=data["item"].standard_cost,
                reference=data["reference"] or f"ADJ-{uuid.uuid4().hex[:10].upper()}",
                notes=data["reason"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Stock adjustment posted.")
            return redirect("inventory:dashboard")
    return render(request, "layouts/form_page.html", {"form": form, "title": "Stock Adjustment", "cancel_url": "/inventory/"})


@role_required(*ROLES)
def stock_transfer(request):
    form = StockTransferForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_stock(posted_by=request.user, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Stock transfer posted.")
            return redirect("inventory:dashboard")
    return render(request, "layouts/form_page.html", {"form": form, "title": "Transfer Stock", "cancel_url": "/inventory/"})
