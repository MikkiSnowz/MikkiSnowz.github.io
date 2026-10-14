import os
import tempfile

_db_dir = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_db_dir}/test.db",
    ADMIN_API_KEY="test-admin-key",
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET="whsec_test",
    DOWNSTREAM_WEBHOOK_URL="https://pos.example.test/orders",
    DOWNSTREAM_WEBHOOK_SECRET="downstream-secret",
    TAX_RATE="0.10",
    TAX_INCLUSIVE="true",
    CARD_SURCHARGE_RATE="0",
    ALLOW_PAY_AT_COUNTER="true",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, DiningTable, ItemOption, MenuItem  # noqa: E402


@pytest.fixture(autouse=True)
def db_data():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        burgers = Category(name="Burgers")
        burger = MenuItem(category=burgers, name="Beef Burger", price_cents=1600, pos_code="BRG1")
        cheese = ItemOption(item=burger, group_name="Extras", name="Extra cheese", price_cents=200)
        sold_out = MenuItem(category=burgers, name="Sold Out Burger", price_cents=1500, is_available=False)
        table = DiningTable(name="Table 1", qr_token="table-one-token")
        db.add_all([burgers, burger, cheese, sold_out, table])
        db.commit()
        yield {"burger": burger.id, "cheese": cheese.id, "sold_out": sold_out.id, "table_token": table.qr_token}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sent_payloads(monkeypatch):
    """Capture what would be sent to the downstream POS instead of making HTTP calls."""
    sent = []
    monkeypatch.setattr("app.integrations.send_to_downstream", lambda payload, settings: sent.append(payload))
    return sent
