import json
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError


PAYSTACK_BASE_URL = "https://api.paystack.co"


def _request(method, endpoint, payload=None):
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")

    if not secret_key:
        raise ValidationError(
            "Paystack secret key is not configured."
        )

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{PAYSTACK_BASE_URL}{endpoint}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Sonoga-HMS/1.0",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        raise ValidationError(
            f"Paystack API error: {body}"
        )

    except urllib.error.URLError as exc:
        raise ValidationError(
            f"Could not connect to Paystack: {exc}"
        )


def initialize_payment(reservation, email):
    amount = Decimal(
        reservation.accommodation_total
    )

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Reservation amount must be greater than zero."
        )

    reference = (
        f"SONOGA-{reservation.reservation_number}-"
        f"{uuid.uuid4().hex[:10].upper()}"
    )

    payload = {
        "email": email,
        "amount": str(
            int(amount * Decimal("100"))
        ),
        "currency": getattr(
            settings,
            "PAYSTACK_CURRENCY",
            "NGN",
        ),
        "reference": reference,
        "callback_url": getattr(
            settings,
            "PAYSTACK_CALLBACK_URL",
            "",
        ),
        "metadata": {
            "reservation_id": reservation.pk,
            "reservation_number": reservation.reservation_number,
            "guest": str(reservation.guest),
        },
    }

    response = _request(
        "POST",
        "/transaction/initialize",
        payload,
    )

    if not response.get("status"):
        raise ValidationError(
            response.get(
                "message",
                "Paystack initialization failed.",
            )
        )

    return response["data"]


def verify_payment(reference):
    response = _request(
        "GET",
        f"/transaction/verify/{reference}",
    )

    if not response.get("status"):
        raise ValidationError(
            response.get(
                "message",
                "Paystack verification failed.",
            )
        )

    return response["data"]
