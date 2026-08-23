from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from control.services import log_event
from inventory.models import StockMovement
from inventory.services import get_stock_balance, post_stock_movement
from .models import FactoryPayment, ProductReturn, SalesInvoice


@transaction.atomic
def confirm_sales_invoice(*, invoice_id: int, confirmed_by) -> SalesInvoice:
    invoice = (
        SalesInvoice.objects.select_for_update()
        .select_related("business_unit", "fulfillment_store")
        .get(pk=invoice_id)
    )
    if invoice.status != SalesInvoice.Status.DRAFT:
        return invoice

    lines = list(invoice.lines.select_related("product", "product__inventory_item"))
    if not lines:
        raise ValidationError("A sales invoice must have at least one line before confirmation.")

    reference = f"SALE:{invoice.invoice_number}"
    if StockMovement.objects.filter(reference=reference, is_void=False).exists():
        raise ValidationError("Stock movements already exist for this invoice. Review before retrying confirmation.")

    for line in lines:
        item = line.product.inventory_item
        available = get_stock_balance(store=invoice.fulfillment_store, item=item, lock=True)
        if available < line.quantity:
            raise ValidationError(
                f"Insufficient {line.product.name}: available {available}, required {line.quantity}."
            )

    for line in lines:
        item = line.product.inventory_item
        post_stock_movement(
            store=invoice.fulfillment_store,
            item=item,
            direction=StockMovement.Direction.OUT,
            movement_type=StockMovement.MovementType.SALE,
            quantity=line.quantity,
            unit_cost=item.standard_cost,
            posted_by=confirmed_by,
            reference=reference,
            notes=f"Factory sale {invoice.invoice_number}",
        )

    invoice.status = SalesInvoice.Status.CONFIRMED
    invoice.save(update_fields=["status", "updated_at"])
    log_event(actor=confirmed_by, business_unit=invoice.business_unit, module="sales", action="confirm", description=f"Confirmed factory sale {invoice.invoice_number} and posted stock movements.", reference_type="SalesInvoice", reference_id=invoice.pk, reference_number=invoice.invoice_number, new_values={"total": str(invoice.net_total)})
    return invoice


@transaction.atomic
def record_factory_payment(*, invoice_id: int, reference: str, amount, method: str, received_by, external_reference="", notes="") -> FactoryPayment:
    invoice = SalesInvoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.status in {SalesInvoice.Status.DRAFT, SalesInvoice.Status.CANCELLED}:
        raise ValidationError("Payments cannot be posted to a draft or cancelled invoice.")

    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")
    if amount > invoice.balance:
        raise ValidationError(f"Payment exceeds invoice balance of {invoice.balance}.")

    payment = FactoryPayment(
        invoice=invoice,
        reference=reference,
        amount=amount,
        method=method,
        status=FactoryPayment.Status.COMPLETED,
        external_reference=external_reference,
        received_by=received_by,
        notes=notes,
    )
    payment.full_clean()
    payment.save()

    invoice.refresh_from_db()
    invoice.status = SalesInvoice.Status.PAID if invoice.balance == 0 else SalesInvoice.Status.PARTIALLY_PAID
    invoice.save(update_fields=["status", "updated_at"])
    log_event(actor=received_by, business_unit=invoice.business_unit, module="sales", action="payment", description=f"Received payment {payment.reference} for {invoice.invoice_number}.", reference_type="FactoryPayment", reference_id=payment.pk, reference_number=payment.reference, new_values={"amount": str(payment.amount), "invoice": invoice.invoice_number})
    return payment


@transaction.atomic
def resolve_product_return(*, return_id: int, destination_store, resolved_by) -> ProductReturn:
    product_return = (
        ProductReturn.objects.select_for_update()
        .select_related("business_unit", "product", "product__inventory_item")
        .get(pk=return_id)
    )
    if product_return.resolution == ProductReturn.Resolution.PENDING:
        raise ValidationError("Choose RESTOCK or WRITE_OFF before resolving the return.")
    if destination_store.business_unit_id != product_return.business_unit_id:
        raise ValidationError("Return destination store must belong to the same business unit.")

    reference = f"RETURN:{product_return.return_number}"
    if StockMovement.objects.filter(reference=reference, is_void=False).exists():
        return product_return

    if product_return.resolution == ProductReturn.Resolution.RESTOCK:
        post_stock_movement(
            store=destination_store,
            item=product_return.product.inventory_item,
            direction=StockMovement.Direction.IN,
            movement_type=StockMovement.MovementType.RETURN_IN,
            quantity=product_return.quantity,
            unit_cost=product_return.product.standard_cost,
            posted_by=resolved_by,
            reference=reference,
            notes=f"Restocked customer return {product_return.return_number}",
        )
    else:
        # Write-offs are recorded as loss events but do not increase usable stock.
        # If physical returned stock is later quarantined, a dedicated quarantine store can be introduced.
        pass

    return product_return
