"""Stripe payments and the shared "order confirmed" step."""

import stripe
from sqlalchemy.orm import Session

from .config import Settings
from .models import Order, OrderStatus, PaymentStatus


def stripe_client(settings: Settings) -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return stripe.StripeClient(settings.stripe_secret_key)


def create_payment_intent(order: Order, settings: Settings) -> stripe.PaymentIntent:
    return stripe_client(settings).v1.payment_intents.create(
        params={
            "amount": order.total_cents,
            "currency": order.currency,
            "automatic_payment_methods": {"enabled": True},
            "metadata": {"order_id": order.public_id, "order_number": order.order_number},
            "description": f"Order {order.order_number}",
            **({"receipt_email": order.customer_email} if order.customer_email else {}),
        },
        options={"idempotency_key": f"order-{order.public_id}"},
    )


def retrieve_payment_intent(payment_intent_id: str, settings: Settings) -> stripe.PaymentIntent:
    return stripe_client(settings).v1.payment_intents.retrieve(payment_intent_id)


def apply_payment_intent(db: Session, order: Order, intent) -> bool:
    """Update an order from a Stripe PaymentIntent.

    Returns True when this call is the one that confirmed the order, so the
    caller knows to send it downstream exactly once.
    """
    # Lock the row: the webhook and the customer's status page can arrive together.
    db.refresh(order, with_for_update=True)
    if intent["id"] != order.stripe_payment_intent_id:
        db.rollback()
        return False
    if intent["amount"] != order.total_cents or intent["currency"] != order.currency:
        # Should never happen; refuse to confirm rather than accept a wrong amount.
        order.payment_status = PaymentStatus.failed
        db.commit()
        return False

    confirmed = False
    if intent["status"] == "succeeded" and order.payment_status != PaymentStatus.paid:
        order.payment_status = PaymentStatus.paid
        if order.status == OrderStatus.awaiting_payment:
            order.status = OrderStatus.placed
        confirmed = True
    elif intent["status"] in ("requires_payment_method", "canceled") and intent.get(
        "last_payment_error"
    ):
        order.payment_status = PaymentStatus.failed
    db.commit()  # also releases the row lock
    return confirmed
