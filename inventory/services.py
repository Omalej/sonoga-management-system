from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from .models import Item, Store, StockMovement


def get_stock_balance(*, store: Store, item: Item, lock: bool = False) -> Decimal:
    qs = StockMovement.objects.filter(store=store, item=item, is_void=False)
    if lock:
        qs = qs.select_for_update()
    total = qs.aggregate(
        total=Sum(
            Case(
                When(direction=StockMovement.Direction.IN, then=F("quantity")),
                When(direction=StockMovement.Direction.OUT, then=-F("quantity")),
                default=Decimal("0.000"),
                output_field=DecimalField(max_digits=18, decimal_places=3),
            )
        )
    )["total"]
    return total or Decimal("0.000")


@transaction.atomic
def post_stock_movement(
    *,
    store: Store,
    item: Item,
    direction: str,
    movement_type: str,
    quantity,
    posted_by,
    unit_cost=Decimal("0.00"),
    reference="",
    notes="",
    allow_negative=False,
) -> StockMovement:
    quantity = Decimal(str(quantity))
    unit_cost = Decimal(str(unit_cost or 0))

    if quantity <= 0:
        raise ValidationError("Stock movement quantity must be greater than zero.")
    if store.business_unit_id != item.business_unit_id:
        raise ValidationError("Item and store must belong to the same business unit.")

    if direction == StockMovement.Direction.OUT and not allow_negative:
        available = get_stock_balance(store=store, item=item, lock=True)
        if available < quantity:
            raise ValidationError(
                f"Insufficient stock for {item.name}. Available: {available}; requested: {quantity}."
            )

    movement = StockMovement(
        store=store,
        item=item,
        direction=direction,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        reference=reference,
        notes=notes,
        posted_by=posted_by,
    )
    movement.full_clean()
    movement.save()
    return movement


@transaction.atomic
def transfer_stock(*, item: Item, source_store: Store, destination_store: Store, quantity, posted_by, reference="", notes=""):
    if source_store.business_unit_id != destination_store.business_unit_id:
        raise ValidationError("Cross-business-unit stock transfers are not allowed in this workflow.")
    if item.business_unit_id != source_store.business_unit_id:
        raise ValidationError("Item must belong to the same business unit as both stores.")

    out_movement = post_stock_movement(
        store=source_store,
        item=item,
        direction=StockMovement.Direction.OUT,
        movement_type=StockMovement.MovementType.TRANSFER_OUT,
        quantity=quantity,
        posted_by=posted_by,
        unit_cost=item.standard_cost,
        reference=reference,
        notes=notes,
    )
    in_movement = post_stock_movement(
        store=destination_store,
        item=item,
        direction=StockMovement.Direction.IN,
        movement_type=StockMovement.MovementType.TRANSFER_IN,
        quantity=quantity,
        posted_by=posted_by,
        unit_cost=item.standard_cost,
        reference=reference,
        notes=notes,
    )
    return out_movement, in_movement
