"""Order total calculation.

Prices always come from the database, never from the browser, so a customer
can't edit the request to pay less.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .models import ItemOption, MenuItem, PaymentMethod
from .schemas import CartLine


class PricingError(ValueError):
    pass


@dataclass
class PricedLine:
    menu_item: MenuItem
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    options: list[dict]
    notes: str | None


@dataclass
class Quote:
    currency: str
    lines: list[PricedLine] = field(default_factory=list)
    subtotal_cents: int = 0
    surcharge_cents: int = 0
    tax_cents: int = 0
    tax_inclusive: bool = True
    total_cents: int = 0


def round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_totals(
    subtotal_cents: int,
    *,
    tax_rate: Decimal,
    tax_inclusive: bool,
    surcharge_rate: Decimal,
) -> tuple[int, int, int]:
    """Return (surcharge_cents, tax_cents, total_cents) for a subtotal."""
    surcharge = round_cents(Decimal(subtotal_cents) * surcharge_rate)
    taxable = Decimal(subtotal_cents + surcharge)
    if tax_inclusive:
        # Prices already include tax; work out the tax portion for the receipt.
        tax = round_cents(taxable * tax_rate / (1 + tax_rate))
        total = subtotal_cents + surcharge
    else:
        tax = round_cents(taxable * tax_rate)
        total = subtotal_cents + surcharge + tax
    return surcharge, tax, total


def price_cart(
    db: Session, lines: list[CartLine], payment_method: PaymentMethod, settings: Settings
) -> Quote:
    item_ids = {line.menu_item_id for line in lines}
    items = {
        item.id: item
        for item in db.scalars(
            select(MenuItem).where(MenuItem.id.in_(item_ids)).options(selectinload(MenuItem.options))
        )
    }

    quote = Quote(currency=settings.currency, tax_inclusive=settings.tax_inclusive)
    for line in lines:
        item = items.get(line.menu_item_id)
        if item is None or not item.is_available:
            raise PricingError(f"Menu item {line.menu_item_id} is not available")

        options_by_id: dict[int, ItemOption] = {o.id: o for o in item.options if o.is_available}
        chosen: list[dict] = []
        for option_id in dict.fromkeys(line.option_ids):  # de-duplicate, keep order
            option = options_by_id.get(option_id)
            if option is None:
                raise PricingError(f"Option {option_id} is not available for {item.name}")
            chosen.append(
                {
                    "id": option.id,
                    "group": option.group_name,
                    "name": option.name,
                    "price_cents": option.price_cents,
                }
            )

        unit = item.price_cents + sum(o["price_cents"] for o in chosen)
        line_total = unit * line.quantity
        quote.lines.append(
            PricedLine(
                menu_item=item,
                quantity=line.quantity,
                unit_price_cents=unit,
                line_total_cents=line_total,
                options=chosen,
                notes=line.notes or None,
            )
        )
        quote.subtotal_cents += line_total

    surcharge_rate = (
        settings.card_surcharge_rate if payment_method == PaymentMethod.card else Decimal("0")
    )
    quote.surcharge_cents, quote.tax_cents, quote.total_cents = calculate_totals(
        quote.subtotal_cents,
        tax_rate=settings.tax_rate,
        tax_inclusive=settings.tax_inclusive,
        surcharge_rate=surcharge_rate,
    )
    return quote
