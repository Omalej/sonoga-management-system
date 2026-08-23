from decimal import Decimal
from django.db.models import F, Sum, ExpressionWrapper, DecimalField, Q
from organization.models import BusinessUnit
from hotel.models import FolioCharge, Payment as HotelPayment, Reservation, Room
from commercial.models import FactoryPayment, SalesInvoice, SalesInvoiceLine
from finance.models import Expense, ExpensePayment
from payroll.models import PayrollRun

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=20, decimal_places=2)


def _sum(qs, field):
    return qs.aggregate(total=Sum(field))["total"] or ZERO


def business_unit_summary(*, business_unit: BusinessUnit, start_date, end_date):
    if business_unit.unit_type == BusinessUnit.UnitType.HOTEL:
        charges = FolioCharge.objects.filter(
            folio__stay__reservation__business_unit=business_unit,
            is_void=False,
            created_at__date__range=(start_date, end_date),
        )
        revenue = _sum(charges, "amount")
        cash_received = _sum(
            HotelPayment.objects.filter(
                Q(folio__stay__reservation__business_unit=business_unit) | Q(reservation__business_unit=business_unit),
                status=HotelPayment.Status.COMPLETED,
                created_at__date__range=(start_date, end_date),
            ),
            "amount",
        )
        outstanding = ZERO
        active_reservations = Reservation.objects.filter(
            business_unit=business_unit,
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN],
        )
        for reservation in active_reservations.select_related("stay").prefetch_related("payments"):
            if hasattr(reservation, "stay") and hasattr(reservation.stay, "folio"):
                outstanding += max(reservation.stay.folio.balance, ZERO)
            else:
                paid = reservation.payments.filter(status=HotelPayment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or ZERO
                outstanding += max(reservation.accommodation_total - paid, ZERO)
        occupied = Room.objects.filter(business_unit=business_unit, occupancy_status=Room.Occupancy.OCCUPIED).count()
        total_rooms = Room.objects.filter(business_unit=business_unit).count()
        operations = {"occupied_rooms": occupied, "total_rooms": total_rooms}
    else:
        line_total_expr = ExpressionWrapper(F("quantity") * F("unit_price") - F("discount_amount"), output_field=MONEY)
        lines = SalesInvoiceLine.objects.filter(
            invoice__business_unit=business_unit,
            invoice__invoice_date__range=(start_date, end_date),
            invoice__status__in=[SalesInvoice.Status.CONFIRMED, SalesInvoice.Status.PARTIALLY_PAID, SalesInvoice.Status.PAID],
        )
        gross_lines = lines.aggregate(total=Sum(line_total_expr))["total"] or ZERO
        invoice_discount = _sum(
            SalesInvoice.objects.filter(
                business_unit=business_unit,
                invoice_date__range=(start_date, end_date),
                status__in=[SalesInvoice.Status.CONFIRMED, SalesInvoice.Status.PARTIALLY_PAID, SalesInvoice.Status.PAID],
            ),
            "discount_amount",
        )
        revenue = max(gross_lines - invoice_discount, ZERO)
        cash_received = _sum(
            FactoryPayment.objects.filter(
                invoice__business_unit=business_unit,
                status=FactoryPayment.Status.COMPLETED,
                created_at__date__range=(start_date, end_date),
            ),
            "amount",
        )
        outstanding = ZERO
        for invoice in SalesInvoice.objects.filter(
            business_unit=business_unit,
            status__in=[SalesInvoice.Status.CONFIRMED, SalesInvoice.Status.PARTIALLY_PAID],
        ).prefetch_related("lines", "payments"):
            outstanding += max(invoice.balance, ZERO)
        operations = {}

    expense_total = _sum(
        Expense.objects.filter(
            business_unit=business_unit,
            expense_date__range=(start_date, end_date),
            status__in=[Expense.Status.APPROVED, Expense.Status.PARTIALLY_PAID, Expense.Status.PAID],
        ),
        "amount",
    )
    expense_cash = _sum(
        ExpensePayment.objects.filter(
            expense__business_unit=business_unit,
            payment_date__range=(start_date, end_date),
            status=ExpensePayment.Status.COMPLETED,
        ),
        "amount",
    )
    payroll_total = ZERO
    for run in PayrollRun.objects.filter(
        business_unit=business_unit,
        period_end__gte=start_date,
        period_start__lte=end_date,
        status__in=[PayrollRun.Status.APPROVED, PayrollRun.Status.PAID],
    ).prefetch_related("lines"):
        payroll_total += run.net_total

    operating_result = revenue - expense_total - payroll_total
    return {
        "business_unit": business_unit,
        "revenue": revenue,
        "cash_received": cash_received,
        "receivables": outstanding,
        "expenses": expense_total,
        "expense_cash_paid": expense_cash,
        "payroll": payroll_total,
        "operating_result": operating_result,
        "operations": operations,
    }


def group_summary(*, start_date, end_date):
    units = BusinessUnit.objects.filter(is_active=True).order_by("name")
    rows = [business_unit_summary(business_unit=unit, start_date=start_date, end_date=end_date) for unit in units]
    totals = {
        "revenue": sum((row["revenue"] for row in rows), ZERO),
        "cash_received": sum((row["cash_received"] for row in rows), ZERO),
        "receivables": sum((row["receivables"] for row in rows), ZERO),
        "expenses": sum((row["expenses"] for row in rows), ZERO),
        "payroll": sum((row["payroll"] for row in rows), ZERO),
        "operating_result": sum((row["operating_result"] for row in rows), ZERO),
    }
    return {"rows": rows, "totals": totals, "start_date": start_date, "end_date": end_date}
