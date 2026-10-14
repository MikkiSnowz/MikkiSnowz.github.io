from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import (
    DispatchStatus,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
    as_utc,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Menu ----------


class OptionOut(ORMModel):
    id: int
    group_name: str
    name: str
    price_cents: int


class MenuItemOut(ORMModel):
    id: int
    name: str
    description: str
    price_cents: int
    image_url: str | None
    options: list[OptionOut]


class CategoryOut(ORMModel):
    id: int
    name: str
    items: list[MenuItemOut]


class TableOut(ORMModel):
    id: int
    name: str


class SettingsOut(BaseModel):
    business_name: str
    currency: str
    tax_rate: float
    tax_inclusive: bool
    card_surcharge_rate: float
    allow_pay_at_counter: bool


class MenuOut(BaseModel):
    settings: SettingsOut
    categories: list[CategoryOut]


# ---------- Ordering ----------


class CartLine(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=50)
    option_ids: list[int] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=255)


class CartIn(BaseModel):
    items: list[CartLine] = Field(min_length=1, max_length=100)
    payment_method: PaymentMethod = PaymentMethod.card


class OrderIn(CartIn):
    table_token: str | None = Field(default=None, max_length=64)
    order_type: OrderType
    customer_name: str = Field(min_length=1, max_length=100)
    customer_phone: str | None = Field(default=None, max_length=30)
    customer_email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def dine_in_needs_table(self):
        if self.order_type == OrderType.dine_in and not self.table_token:
            raise ValueError("Dine-in orders must come from a table QR code")
        return self


class QuoteLineOut(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    options: list[dict]
    notes: str | None


class QuoteOut(BaseModel):
    currency: str
    lines: list[QuoteLineOut]
    subtotal_cents: int
    surcharge_cents: int
    tax_cents: int
    tax_inclusive: bool
    total_cents: int


class OrderItemOut(ORMModel):
    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    options: list[dict]
    notes: str | None


class OrderOut(ORMModel):
    public_id: str
    order_number: str
    table: TableOut | None
    order_type: OrderType
    customer_name: str
    notes: str | None
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    currency: str
    subtotal_cents: int
    surcharge_cents: int
    tax_cents: int
    tax_inclusive: bool
    total_cents: int
    items: list[OrderItemOut]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def created_at_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class OrderCreatedOut(BaseModel):
    order: OrderOut
    # Present for card payments: the frontend hands it to Stripe's Payment Element.
    stripe_client_secret: str | None = None


# ---------- Staff ----------


class StaffOrderOut(OrderOut):
    id: int
    customer_phone: str | None
    customer_email: str | None
    dispatch_status: DispatchStatus
    dispatch_attempts: int
    dispatch_error: str | None


class StatusUpdateIn(BaseModel):
    status: OrderStatus


class TableAdminOut(ORMModel):
    id: int
    name: str
    qr_token: str
    is_active: bool
    order_url: str
    qr_png_url: str


class TableCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
