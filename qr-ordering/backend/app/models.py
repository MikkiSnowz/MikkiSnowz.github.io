"""Database tables. All money is stored as integer cents to avoid rounding errors."""

import enum
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """MySQL DATETIME drops the timezone; everything is stored in UTC, so put it back."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class OrderType(str, enum.Enum):
    dine_in = "dine_in"
    takeaway = "takeaway"


class PaymentMethod(str, enum.Enum):
    card = "card"
    counter = "counter"


class OrderStatus(str, enum.Enum):
    awaiting_payment = "awaiting_payment"  # card order created, Stripe not yet paid
    placed = "placed"  # confirmed and sent to the kitchen/POS
    preparing = "preparing"
    ready = "ready"
    completed = "completed"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class DispatchStatus(str, enum.Enum):
    not_sent = "not_sent"
    sent = "sent"
    failed = "failed"
    disabled = "disabled"  # no downstream system configured


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    items: Mapped[list["MenuItem"]] = relationship(
        back_populates="category", order_by="MenuItem.sort_order"
    )


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    price_cents: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # Code used by your POS for this product, sent along in the downstream payload.
    pos_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    category: Mapped[Category] = relationship(back_populates="items")
    options: Mapped[list["ItemOption"]] = relationship(
        back_populates="item", order_by="ItemOption.sort_order"
    )


class ItemOption(Base):
    """An add-on or variation for an item, e.g. "Extra cheese (+$2)" or "Oat milk"."""

    __tablename__ = "item_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    group_name: Mapped[str] = mapped_column(String(100), default="Extras")
    name: Mapped[str] = mapped_column(String(100))
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    item: Mapped[MenuItem] = relationship(back_populates="options")


class DiningTable(Base):
    __tablename__ = "dining_tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    # Random, unguessable token printed in the QR code (so people can't spoof other tables).
    qr_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(12)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Public id used in URLs so customers can't enumerate other people's orders.
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    table_id: Mapped[int | None] = mapped_column(ForeignKey("dining_tables.id"), nullable=True)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType))
    customer_name: Mapped[str] = mapped_column(String(100))
    customer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.unpaid
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    currency: Mapped[str] = mapped_column(String(3))
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    surcharge_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean)
    total_cents: Mapped[int] = mapped_column(Integer)

    dispatch_status: Mapped[DispatchStatus] = mapped_column(
        Enum(DispatchStatus), default=DispatchStatus.not_sent
    )
    dispatch_attempts: Mapped[int] = mapped_column(Integer, default=0)
    dispatch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    table: Mapped[DiningTable | None] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def order_number(self) -> str:
        """Short number to call out at the counter."""
        return f"{self.id % 1000:03d}"


class OrderItem(Base):
    """A line on an order. Names and prices are copied so later menu edits don't change history."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(150))
    pos_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_cents: Mapped[int] = mapped_column(Integer)  # item price + selected options
    line_total_cents: Mapped[int] = mapped_column(Integer)
    # [{"id": 3, "group": "Milk", "name": "Oat milk", "price_cents": 80}, ...]
    options: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")
