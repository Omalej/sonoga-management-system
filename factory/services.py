from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from control.services import log_event
from inventory.models import StockMovement
from inventory.services import get_stock_balance, post_stock_movement
from .models import ProductionBatch


@transaction.atomic
def approve_production_batch(*, batch_id: int, approved_by) -> ProductionBatch:
    batch = (
        ProductionBatch.objects.select_for_update()
        .select_related(
            "business_unit", "product", "product__inventory_item",
            "raw_material_store", "finished_goods_store"
        )
        .get(pk=batch_id)
    )

    if batch.status == ProductionBatch.Status.APPROVED:
        return batch
    if batch.status not in {ProductionBatch.Status.COMPLETED, ProductionBatch.Status.SUBMITTED}:
        raise ValidationError("Only completed or submitted production batches can be approved.")
    if batch.accepted_quantity <= 0:
        raise ValidationError("Accepted production quantity must be greater than zero before approval.")

    reference = f"PROD:{batch.batch_number}"
    if StockMovement.objects.filter(reference=reference, is_void=False).exists():
        raise ValidationError("Stock movements already exist for this production batch. Review before retrying approval.")

    usages = list(batch.material_usages.select_related("item"))
    for usage in usages:
        available = get_stock_balance(store=batch.raw_material_store, item=usage.item, lock=True)
        if available < usage.quantity:
            raise ValidationError(
                f"Insufficient {usage.item.name}: available {available}, required {usage.quantity}."
            )

    for usage in usages:
        post_stock_movement(
            store=batch.raw_material_store,
            item=usage.item,
            direction=StockMovement.Direction.OUT,
            movement_type=StockMovement.MovementType.PRODUCTION_ISSUE,
            quantity=usage.quantity,
            unit_cost=usage.unit_cost or usage.item.standard_cost,
            posted_by=approved_by,
            reference=reference,
            notes=f"Material issued for batch {batch.batch_number}",
        )

    finished_item = batch.product.inventory_item
    output_unit_cost = batch.product.standard_cost or Decimal("0.00")
    post_stock_movement(
        store=batch.finished_goods_store,
        item=finished_item,
        direction=StockMovement.Direction.IN,
        movement_type=StockMovement.MovementType.PRODUCTION_OUTPUT,
        quantity=batch.accepted_quantity,
        unit_cost=output_unit_cost,
        posted_by=approved_by,
        reference=reference,
        notes=f"Accepted output from batch {batch.batch_number}",
    )

    batch.status = ProductionBatch.Status.APPROVED
    batch.approved_by = approved_by
    batch.save(update_fields=["status", "approved_by", "updated_at"])
    log_event(actor=approved_by, business_unit=batch.business_unit, module="production", action="approve", description=f"Approved production batch {batch.batch_number} and posted inventory movements.", reference_type="ProductionBatch", reference_id=batch.pk, reference_number=batch.batch_number, new_values={"accepted_quantity": str(batch.accepted_quantity), "rejected_quantity": str(batch.rejected_quantity)})
    return batch
