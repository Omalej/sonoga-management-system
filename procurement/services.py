from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from inventory.models import StockMovement
from inventory.services import post_stock_movement
from .models import GoodsReceipt, PurchaseOrder, PurchaseRequest


@transaction.atomic
def approve_purchase_request(*, request_id: int, approved_by) -> PurchaseRequest:
    purchase_request = PurchaseRequest.objects.select_for_update().get(pk=request_id)
    if purchase_request.status == PurchaseRequest.Status.APPROVED:
        return purchase_request
    if purchase_request.status != PurchaseRequest.Status.SUBMITTED:
        raise ValidationError("Only submitted purchase requests can be approved.")
    if not purchase_request.lines.exists():
        raise ValidationError("Purchase request has no items.")
    purchase_request.status = PurchaseRequest.Status.APPROVED
    purchase_request.approved_by = approved_by
    purchase_request.approved_at = timezone.now()
    purchase_request.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return purchase_request


@transaction.atomic
def post_goods_receipt(*, receipt_id: int, posted_by) -> GoodsReceipt:
    receipt = GoodsReceipt.objects.select_for_update().select_related("purchase_order", "destination_store").get(pk=receipt_id)
    if receipt.status == GoodsReceipt.Status.POSTED:
        return receipt
    if receipt.status != GoodsReceipt.Status.DRAFT:
        raise ValidationError("Only draft goods receipts can be posted.")
    if receipt.purchase_order.status not in {PurchaseOrder.Status.ISSUED, PurchaseOrder.Status.PART_RECEIVED}:
        raise ValidationError("Goods can only be received against an issued purchase order.")
    lines = list(receipt.lines.select_related("order_line", "order_line__item"))
    if not lines:
        raise ValidationError("Goods receipt has no lines.")

    reference = f"GRN:{receipt.receipt_number}"
    if StockMovement.objects.filter(reference=reference, is_void=False).exists():
        raise ValidationError("Stock movements already exist for this goods receipt.")

    # Prevent cumulative accepted quantity from exceeding the ordered quantity.
    for line in lines:
        prior = line.order_line.receipt_lines.filter(receipt__status=GoodsReceipt.Status.POSTED).exclude(receipt=receipt).aggregate(v=Sum("quantity_received"))["v"] or Decimal("0.000")
        prior_rejected = line.order_line.receipt_lines.filter(receipt__status=GoodsReceipt.Status.POSTED).exclude(receipt=receipt).aggregate(v=Sum("quantity_rejected"))["v"] or Decimal("0.000")
        prior_accepted = prior - prior_rejected
        if prior_accepted + line.accepted_quantity > line.order_line.quantity:
            raise ValidationError(f"Receipt quantity exceeds ordered quantity for {line.order_line.item.name}.")

    for line in lines:
        if line.accepted_quantity <= 0:
            continue
        post_stock_movement(
            store=receipt.destination_store,
            item=line.order_line.item,
            direction=StockMovement.Direction.IN,
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity=line.accepted_quantity,
            unit_cost=line.order_line.unit_cost,
            posted_by=posted_by,
            reference=reference,
            notes=f"Goods receipt {receipt.receipt_number}",
        )

    receipt.status = GoodsReceipt.Status.POSTED
    receipt.posted_by = posted_by
    receipt.save(update_fields=["status", "posted_by", "updated_at"])

    order = receipt.purchase_order
    fully_received = True
    for order_line in order.lines.all():
        received = order_line.receipt_lines.filter(receipt__status=GoodsReceipt.Status.POSTED).aggregate(v=Sum("quantity_received"))["v"] or Decimal("0.000")
        rejected = order_line.receipt_lines.filter(receipt__status=GoodsReceipt.Status.POSTED).aggregate(v=Sum("quantity_rejected"))["v"] or Decimal("0.000")
        if received - rejected < order_line.quantity:
            fully_received = False
            break
    order.status = PurchaseOrder.Status.RECEIVED if fully_received else PurchaseOrder.Status.PART_RECEIVED
    order.save(update_fields=["status", "updated_at"])
    return receipt
