ADMIN = {"X-Admin-Key": "test-admin-key"}


def order_body(ids, **overrides):
    body = {
        "table_token": ids["table_token"],
        "order_type": "dine_in",
        "customer_name": "Sam",
        "payment_method": "counter",
        "items": [{"menu_item_id": ids["burger"], "quantity": 2, "option_ids": [ids["cheese"]]}],
    }
    body.update(overrides)
    return body


def test_menu_hides_unavailable_items(client):
    menu = client.get("/api/menu").json()
    names = [i["name"] for c in menu["categories"] for i in c["items"]]
    assert names == ["Beef Burger"]


def test_quote_uses_server_prices(client, db_data):
    res = client.post(
        "/api/orders/quote",
        json={"items": [{"menu_item_id": db_data["burger"], "quantity": 2, "option_ids": [db_data["cheese"]]}]},
    )
    assert res.status_code == 200
    quote = res.json()
    assert quote["lines"][0]["unit_price_cents"] == 1800
    assert quote["subtotal_cents"] == 3600
    assert quote["total_cents"] == 3600
    assert quote["tax_cents"] == 327  # GST included: 3600 / 11


def test_rejects_unavailable_item_and_foreign_option(client, db_data):
    res = client.post("/api/orders/quote", json={"items": [{"menu_item_id": db_data["sold_out"], "quantity": 1}]})
    assert res.status_code == 422
    res = client.post(
        "/api/orders/quote",
        json={"items": [{"menu_item_id": db_data["burger"], "quantity": 1, "option_ids": [9999]}]},
    )
    assert res.status_code == 422


def test_invalid_table_token(client, db_data):
    res = client.post("/api/orders", json=order_body(db_data, table_token="nope"))
    assert res.status_code == 404


def test_dine_in_requires_table(client, db_data):
    res = client.post("/api/orders", json=order_body(db_data, table_token=None))
    assert res.status_code == 422


def test_pay_at_counter_order_is_sent_downstream(client, db_data, sent_payloads):
    res = client.post("/api/orders", json=order_body(db_data))
    assert res.status_code == 201
    order = res.json()["order"]
    assert order["status"] == "placed"
    assert order["total_cents"] == 3600
    assert order["table"]["name"] == "Table 1"

    assert len(sent_payloads) == 1
    payload = sent_payloads[0]
    assert payload["order_id"] == order["public_id"]
    assert payload["table"] == "Table 1"
    assert payload["items"][0]["pos_code"] == "BRG1"
    assert payload["items"][0]["options"][0]["name"] == "Extra cheese"

    staff = client.get("/api/admin/orders", headers=ADMIN).json()
    assert staff[0]["dispatch_status"] == "sent"


def test_card_order_dispatched_only_after_payment(client, db_data, sent_payloads, monkeypatch):
    intent = {"id": "pi_123", "client_secret": "pi_123_secret", "amount": 3600, "currency": "aud", "status": "requires_payment_method"}
    monkeypatch.setattr("app.routers.public.create_payment_intent", lambda order, settings: intent)
    monkeypatch.setattr("app.routers.public.retrieve_payment_intent", lambda pid, settings: intent)

    res = client.post("/api/orders", json=order_body(db_data, payment_method="card"))
    assert res.status_code == 201
    data = res.json()
    assert data["stripe_client_secret"] == "pi_123_secret"
    public_id = data["order"]["public_id"]
    assert data["order"]["status"] == "awaiting_payment"
    assert sent_payloads == []

    # Not paid yet: polling the order changes nothing.
    assert client.get(f"/api/orders/{public_id}").json()["status"] == "awaiting_payment"

    intent["status"] = "succeeded"
    order = client.get(f"/api/orders/{public_id}").json()
    assert order["status"] == "placed"
    assert order["payment_status"] == "paid"
    assert len(sent_payloads) == 1

    # Polling again doesn't send it twice.
    client.get(f"/api/orders/{public_id}")
    assert len(sent_payloads) == 1


def test_stripe_amount_mismatch_is_not_accepted(client, db_data, sent_payloads, monkeypatch):
    intent = {"id": "pi_456", "client_secret": "s", "amount": 1, "currency": "aud", "status": "succeeded"}
    monkeypatch.setattr("app.routers.public.create_payment_intent", lambda order, settings: intent)
    monkeypatch.setattr("app.routers.public.retrieve_payment_intent", lambda pid, settings: intent)
    public_id = client.post("/api/orders", json=order_body(db_data, payment_method="card")).json()["order"]["public_id"]
    order = client.get(f"/api/orders/{public_id}").json()
    assert order["status"] == "awaiting_payment"
    assert sent_payloads == []


def test_failed_dispatch_is_recorded_and_can_be_retried(client, db_data, monkeypatch):
    def boom(payload, settings):
        raise ConnectionError("POS offline")

    monkeypatch.setattr("app.integrations.send_to_downstream", boom)
    client.post("/api/orders", json=order_body(db_data))
    order = client.get("/api/admin/orders", headers=ADMIN).json()[0]
    assert order["dispatch_status"] == "failed"
    assert "POS offline" in order["dispatch_error"]

    monkeypatch.setattr("app.integrations.send_to_downstream", lambda payload, settings: None)
    retried = client.post(f"/api/admin/orders/{order['id']}/dispatch", headers=ADMIN).json()
    assert retried["dispatch_status"] == "sent"
    assert retried["dispatch_attempts"] == 2


def test_admin_requires_key(client):
    assert client.get("/api/admin/orders").status_code == 401
    assert client.get("/api/admin/orders", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_table_qr_png(client):
    tables = client.get("/api/admin/tables", headers=ADMIN).json()
    assert tables[0]["order_url"].endswith("/t/table-one-token")
    res = client.get(tables[0]["qr_png_url"], headers=ADMIN)
    assert res.status_code == 200
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_status_update(client, db_data, sent_payloads):
    client.post("/api/orders", json=order_body(db_data))
    order_id = client.get("/api/admin/orders", headers=ADMIN).json()[0]["id"]
    res = client.patch(f"/api/admin/orders/{order_id}/status", json={"status": "ready"}, headers=ADMIN)
    assert res.json()["status"] == "ready"


def test_stripe_webhook_rejects_bad_signature(client):
    res = client.post("/api/webhooks/stripe", content=b"{}", headers={"Stripe-Signature": "t=1,v1=bad"})
    assert res.status_code == 400


def test_stripe_webhook_confirms_payment(client, db_data, sent_payloads, monkeypatch):
    import hashlib
    import hmac
    import json
    import time

    intent = {"id": "pi_789", "object": "payment_intent", "client_secret": "s", "amount": 3600, "currency": "aud", "status": "requires_payment_method"}
    monkeypatch.setattr("app.routers.public.create_payment_intent", lambda order, settings: intent)
    public_id = client.post("/api/orders", json=order_body(db_data, payment_method="card")).json()["order"]["public_id"]

    event = {
        "id": "evt_1",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {"object": {**intent, "status": "succeeded"}},
    }
    payload = json.dumps(event)
    ts = int(time.time())
    sig = hmac.new(b"whsec_test", f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    res = client.post("/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": f"t={ts},v1={sig}"})
    assert res.status_code == 200

    monkeypatch.setattr("app.routers.public.retrieve_payment_intent", lambda pid, settings: {**intent, "status": "succeeded"})
    order = client.get(f"/api/orders/{public_id}").json()
    assert order["payment_status"] == "paid"
    assert len(sent_payloads) == 1
