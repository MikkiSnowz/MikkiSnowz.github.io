"""Endpoints used by customers after scanning a QR code."""

import logging

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..database import SessionLocal, get_db
from ..integrations import dispatch_order
from ..models import (
    Category,
    DiningTable,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderType,
    PaymentMethod,
)
from ..payments import apply_payment_intent, create_payment_intent, retrieve_payment_intent
from ..pricing import PricingError, Quote, price_cart
from ..schemas import (
    CartIn,
    CategoryOut,
    MenuItemOut,
    MenuOut,
    OptionOut,
    OrderCreatedOut,
    OrderIn,
    OrderOut,
    QuoteLineOut,
    QuoteOut,
    SettingsOut,
    TableOut,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["customer"])


def dispatch_in_background(order_id: int) -> None:
    """Runs after the response is sent, with its own DB session."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is not None:
            dispatch_order(db, order, get_settings())


def get_active_table(db: Session, token: str) -> DiningTable:
    table = db.scalar(select(DiningTable).where(DiningTable.qr_token == token))
    if table is None or not table.is_active:
        raise HTTPException(404, "This table QR code is not valid. Please ask staff for help.")
    return table


def quote_out(quote: Quote) -> QuoteOut:
    return QuoteOut(
        currency=quote.currency,
        lines=[
            QuoteLineOut(
                menu_item_id=line.menu_item.id,
                name=line.menu_item.name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                line_total_cents=line.line_total_cents,
                options=line.options,
                notes=line.notes,
            )
            for line in quote.lines
        ],
        subtotal_cents=quote.subtotal_cents,
        surcharge_cents=quote.surcharge_cents,
        tax_cents=quote.tax_cents,
        tax_inclusive=quote.tax_inclusive,
        total_cents=quote.total_cents,
    )


def check_payment_method(method: PaymentMethod, settings: Settings) -> None:
    if method == PaymentMethod.counter and not settings.allow_pay_at_counter:
        raise HTTPException(400, "Paying at the counter is not available")


@router.get("/menu", response_model=MenuOut)
def get_menu(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    categories = db.scalars(
        select(Category)
        .order_by(Category.sort_order, Category.id)
        .options(selectinload(Category.items).selectinload(MenuItem.options))
    ).all()
    return MenuOut(
        settings=SettingsOut(
            business_name=settings.business_name,
            currency=settings.currency,
            tax_rate=float(settings.tax_rate),
            tax_inclusive=settings.tax_inclusive,
            card_surcharge_rate=float(settings.card_surcharge_rate),
            allow_pay_at_counter=settings.allow_pay_at_counter,
        ),
        categories=[
            CategoryOut(
                id=c.id,
                name=c.name,
                items=[
                    MenuItemOut(
                        id=i.id,
                        name=i.name,
                        description=i.description,
                        price_cents=i.price_cents,
                        image_url=i.image_url,
                        options=[OptionOut.model_validate(o) for o in i.options if o.is_available],
                    )
                    for i in c.items
                    if i.is_available
                ],
            )
            for c in categories
        ],
    )


@router.get("/tables/{token}", response_model=TableOut)
def get_table(token: str, db: Session = Depends(get_db)):
    return get_active_table(db, token)


@router.post("/orders/quote", response_model=QuoteOut)
def quote_order(
    cart: CartIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Calculate the total for a cart without creating an order."""
    check_payment_method(cart.payment_method, settings)
    try:
        return quote_out(price_cart(db, cart.items, cart.payment_method, settings))
    except PricingError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/orders", response_model=OrderCreatedOut, status_code=201)
def create_order(
    data: OrderIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    check_payment_method(data.payment_method, settings)
    table = get_active_table(db, data.table_token) if data.table_token else None
    # A takeaway order can still come from a table QR; only keep the table for dine-in.
    if data.order_type == OrderType.takeaway:
        table = None

    try:
        quote = price_cart(db, data.items, data.payment_method, settings)
    except PricingError as exc:
        raise HTTPException(422, str(exc)) from exc

    paying_now = data.payment_method == PaymentMethod.card
    order = Order(
        table=table,
        order_type=data.order_type,
        customer_name=data.customer_name.strip(),
        customer_phone=data.customer_phone,
        customer_email=data.customer_email,
        notes=data.notes,
        status=OrderStatus.awaiting_payment if paying_now else OrderStatus.placed,
        payment_method=data.payment_method,
        currency=quote.currency,
        subtotal_cents=quote.subtotal_cents,
        surcharge_cents=quote.surcharge_cents,
        tax_cents=quote.tax_cents,
        tax_inclusive=quote.tax_inclusive,
        total_cents=quote.total_cents,
        items=[
            OrderItem(
                menu_item_id=line.menu_item.id,
                name=line.menu_item.name,
                pos_code=line.menu_item.pos_code,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                line_total_cents=line.line_total_cents,
                options=line.options,
                notes=line.notes,
            )
            for line in quote.lines
        ],
    )
    db.add(order)
    db.commit()

    client_secret = None
    if paying_now:
        try:
            intent = create_payment_intent(order, settings)
        except (stripe.StripeError, RuntimeError) as exc:
            log.exception("Could not create PaymentIntent for order %s", order.public_id)
            order.status = OrderStatus.cancelled
            db.commit()
            raise HTTPException(502, "Payment service unavailable, please try again") from exc
        order.stripe_payment_intent_id = intent["id"]
        db.commit()
        client_secret = intent["client_secret"]
    else:
        background.add_task(dispatch_in_background, order.id)

    return OrderCreatedOut(order=OrderOut.model_validate(order), stripe_client_secret=client_secret)


@router.get("/orders/{public_id}", response_model=OrderOut)
def get_order(
    public_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    order = db.scalar(select(Order).where(Order.public_id == public_id))
    if order is None:
        raise HTTPException(404, "Order not found")

    # Normally the Stripe webhook confirms payment. Checking here as well means the
    # customer sees "paid" straight away, and it still works if a webhook is delayed.
    if order.status == OrderStatus.awaiting_payment and order.stripe_payment_intent_id:
        try:
            intent = retrieve_payment_intent(order.stripe_payment_intent_id, settings)
        except (stripe.StripeError, RuntimeError):
            log.warning("Could not check PaymentIntent for order %s", order.public_id)
        else:
            if apply_payment_intent(db, order, intent):
                background.add_task(dispatch_in_background, order.id)
    return order
