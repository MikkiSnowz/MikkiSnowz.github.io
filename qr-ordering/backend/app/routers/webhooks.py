"""Stripe tells us here when a payment succeeds or fails."""

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import Order
from ..payments import apply_payment_intent, stripe_client
from .public import dispatch_in_background

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

HANDLED_EVENTS = {"payment_intent.succeeded", "payment_intent.payment_failed"}


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background: BackgroundTasks,
    stripe_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, "Stripe webhook secret not configured")
    payload = await request.body()
    try:
        event = stripe_client(settings).construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid Stripe signature") from exc

    if event.type in HANDLED_EVENTS:
        intent = event.data.object
        order = db.scalar(select(Order).where(Order.stripe_payment_intent_id == intent["id"]))
        if order is not None and apply_payment_intent(db, order, intent):
            background.add_task(dispatch_in_background, order.id)

    return {"received": True}
