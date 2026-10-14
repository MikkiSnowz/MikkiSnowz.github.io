from decimal import Decimal

from app.pricing import calculate_totals


def test_tax_inclusive_extracts_gst():
    surcharge, tax, total = calculate_totals(
        1100, tax_rate=Decimal("0.10"), tax_inclusive=True, surcharge_rate=Decimal("0")
    )
    assert (surcharge, tax, total) == (0, 100, 1100)


def test_tax_exclusive_adds_tax():
    surcharge, tax, total = calculate_totals(
        1000, tax_rate=Decimal("0.0825"), tax_inclusive=False, surcharge_rate=Decimal("0")
    )
    assert (surcharge, tax, total) == (0, 83, 1083)  # 82.5 rounds half up


def test_card_surcharge_is_added_and_taxed():
    surcharge, tax, total = calculate_totals(
        2000, tax_rate=Decimal("0.10"), tax_inclusive=True, surcharge_rate=Decimal("0.015")
    )
    assert surcharge == 30
    assert total == 2030
    assert tax == 185  # 2030 / 11 = 184.5 -> 185
