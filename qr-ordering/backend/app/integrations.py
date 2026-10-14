"""Hand confirmed orders to another system (POS, kitchen display, accounting...).

Each confirmed order is POSTed as JSON to DOWNSTREAM_WEBHOOK_URL. The raw body is
signed with HMAC-SHA256 using DOWNSTREAM_WEBHOOK_SECRET and sent in the
``X-Signature`` header so the receiver can check it really came from us.

To talk to a POS with its own API instead, replace ``send_to_downstream`` with a
call to that API; everything else stays the same.
"""

import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy.orm import Session

from .config import Settings
from .models import DispatchStatus, Order, as_utc, utcnow

log = logging.getLogger(__name__)


def build_payload(order: Order) -> dict:
    return {
        "event": "order.confirmed",
        "order_id": order.public_id,
        "order_number": order.order_number,
        "order_type": order.order_type.value,
        "table": order.table.name if order.table else None,
        "customer": {
            "name": order.customer_name,
            "phone": order.customer_phone,
            "email": order.customer_email,
        },
        "notes": order.notes,
        "payment": {
            "method": order.payment_method.value,
            "status": order.payment_status.value,
            "stripe_payment_intent_id": order.stripe_payment_intent_id,
        },
        "currency": order.currency,
        "subtotal_cents": order.subtotal_cents,
        "surcharge_cents": order.surcharge_cents,
        "tax_cents": order.tax_cents,
        "tax_inclusive": order.tax_inclusive,
        "total_cents": order.total_cents,
        "items": [
            {
                "menu_item_id": line.menu_item_id,
                "pos_code": line.pos_code,
                "name": line.name,
                "quantity": line.quantity,
                "unit_price_cents": line.unit_price_cents,
                "line_total_cents": line.line_total_cents,
                "options": line.options,
                "notes": line.notes,
            }
            for line in order.items
        ],
        "created_at": as_utc(order.created_at).isoformat(),
    }


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_to_downstream(payload: dict, settings: Settings) -> None:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": sign(body, settings.downstream_webhook_secret),
        "Idempotency-Key": payload["order_id"],
    }
    response = httpx.post(
        settings.downstream_webhook_url,
        content=body,
        headers=headers,
        timeout=settings.downstream_timeout_seconds,
    )
    response.raise_for_status()


def dispatch_order(db: Session, order: Order, settings: Settings) -> None:
    """Send an order downstream and record the outcome on the order."""
    if order.dispatch_status == DispatchStatus.sent:
        return
    if not settings.downstream_webhook_url:
        order.dispatch_status = DispatchStatus.disabled
        db.commit()
        return

    order.dispatch_attempts += 1
    try:
        send_to_downstream(build_payload(order), settings)
    except Exception as exc:  # noqa: BLE001 - any failure should be recorded, not crash
        log.exception("Failed to dispatch order %s", order.public_id)
        order.dispatch_status = DispatchStatus.failed
        order.dispatch_error = str(exc)[:2000]
    else:
        order.dispatch_status = DispatchStatus.sent
        order.dispatch_error = None
        order.dispatched_at = utcnow()
    db.commit()
