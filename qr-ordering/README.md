# QR Ordering System

A QR-code ordering system for a local restaurant or café, similar to Abacus Online Ordering.

1. The customer scans the QR code on their table (or the takeaway QR at the counter).
2. The React web app opens with the menu. They pick items and add-ons, then enter their name and any notes.
3. The **Python backend works out the total** from prices in MySQL. It never trusts prices sent by the browser, and it handles tax (GST included or added) and an optional card surcharge.
4. They either pay by card with **Stripe** or choose to pay at the counter.
5. Once the order is confirmed, the backend **sends it to your other system** (POS, kitchen display, accounting) as signed JSON.
6. Staff see live order tickets at `/staff`, move them through *preparing → ready → completed*, and the customer's screen updates.

```
 QR code ──► React app ──► FastAPI (Python) ──► MySQL
                │              │
                └── Stripe ◄───┤  (PaymentIntent + webhook)
                               └──► Your POS / other system (signed webhook)
```

| Part     | Tech                                   | Folder      |
| -------- | -------------------------------------- | ----------- |
| Frontend | React 19 + Vite, Stripe Payment Element | `frontend/` |
| Backend  | Python, FastAPI, SQLAlchemy            | `backend/`  |
| Database | MySQL 8                                | `docker-compose.yml` |
| Payments | Stripe                                 | `backend/app/payments.py` |
| QR codes | `qrcode` Python library                | `backend/app/qr.py` |

## Running it locally

### 1. MySQL

```sh
docker compose up -d
```

This starts MySQL on port **3307**, with the database `qr_ordering` and user `qr_user` already created. It uses 3307 so it doesn't clash with a MySQL you may already have on 3306. Wait about 20 seconds for it to start the first time.

To use a MySQL server you already have instead, create the database and user in it, then point `DATABASE_URL` at it:

```sql
CREATE DATABASE qr_ordering;
CREATE USER 'qr_user'@'localhost' IDENTIFIED BY 'qr_password';
GRANT ALL ON qr_ordering.* TO 'qr_user'@'localhost';
```

### 2. Backend

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 seed.py
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```sh
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Customer view: open one of the table URLs that `seed.py` printed, e.g. `http://localhost:5173/t/<token>`, or `/takeaway`.
- Staff view: http://localhost:5173/staff. Log in with your `ADMIN_API_KEY`. The **Tables & QR codes** tab lets you download a printable QR code for each table.

To try it on your phone, set `FRONTEND_URL` to `http://<your-computer-ip>:5173`, restart the backend, and scan a QR code from the staff page.

### 4. Stripe (card payments)

1. Copy your test keys from https://dashboard.stripe.com/test/apikeys. Put `sk_test_…` in `backend/.env` and `pk_test_…` in `frontend/.env`.
2. Forward webhooks to your laptop with the [Stripe CLI](https://docs.stripe.com/stripe-cli):
   ```sh
   stripe listen --forward-to localhost:8000/api/webhooks/stripe
   ```
   Put the `whsec_…` it prints into `STRIPE_WEBHOOK_SECRET`.
3. Pay with the test card `4242 4242 4242 4242`, any future expiry date, and any CVC.

The order status page also checks Stripe directly, so payments still go through locally if the webhook isn't running. Run the webhook in production anyway.

### Something not working?

Open http://localhost:8000/api/health. It reports whether the backend can reach MySQL and, if it can't, what to fix (MySQL not running, wrong password, tables not created yet). The frontend shows the same messages instead of a bare error code.

On macOS, the terminal doesn't ignore `# comments` you paste after a command, so copy only the command itself.

### Tests

```sh
cd backend && pytest
```

## How the total is calculated

`backend/app/pricing.py`, with everything in integer cents:

```
line total = (item price + selected add-ons) × quantity
subtotal   = sum of line totals
surcharge  = subtotal × CARD_SURCHARGE_RATE        (card payments only)
TAX_INCLUSIVE=true  → total = subtotal + surcharge; tax = total × rate / (1 + rate)   (AU/NZ GST style)
TAX_INCLUSIVE=false → tax = (subtotal + surcharge) × rate; total = subtotal + surcharge + tax
```

The browser calls `POST /api/orders/quote` to show the total before checkout. `POST /api/orders` recalculates it from scratch, and that figure is what Stripe charges.

## Passing orders to another system

When an order is confirmed (a card payment succeeded, or a pay-at-counter order was placed), the backend POSTs this JSON to `DOWNSTREAM_WEBHOOK_URL`:

```json
{
  "event": "order.confirmed",
  "order_id": "ccc24c87-15e9-4ee6-9b8b-1a727ad89fa1",
  "order_number": "001",
  "order_type": "dine_in",
  "table": "Table 1",
  "customer": { "name": "Sam", "phone": null, "email": null },
  "notes": "Window seat",
  "payment": { "method": "counter", "status": "unpaid", "stripe_payment_intent_id": null },
  "currency": "aud",
  "subtotal_cents": 4180, "surcharge_cents": 0, "tax_cents": 380, "tax_inclusive": true, "total_cents": 4180,
  "items": [
    {
      "menu_item_id": 2, "pos_code": "BEEF01", "name": "Chilli Beef Burger", "quantity": 2,
      "unit_price_cents": 1800, "line_total_cents": 3600,
      "options": [{ "id": 3, "group": "Extras", "name": "Extra cheese", "price_cents": 200 }],
      "notes": null
    }
  ],
  "created_at": "2026-10-14T12:29:29+00:00"
}
```

- **Signature:** the `X-Signature` header is `HMAC-SHA256(DOWNSTREAM_WEBHOOK_SECRET, raw body)` in hex. Check it on the receiving side.
- **Idempotency:** the `Idempotency-Key` header is the order id, so the receiver can ignore duplicates.
- **Failures:** if the other system is down, the order is still saved. The staff page shows "Not sent to POS" with a **Retry** button (`POST /api/admin/orders/{id}/dispatch`).
- **POS codes:** set `menu_items.pos_code` so each line maps to the matching product in your POS.
- **A POS with its own API:** if the other system needs its own API call instead of a webhook (e.g. Square, Lightspeed or a local printer service), replace `send_to_downstream()` in `backend/app/integrations.py`. Nothing else needs to change.

## API overview

| Method | Path | Who | Purpose |
| ------ | ---- | --- | ------- |
| GET  | `/api/menu` | customer | Menu + business settings |
| GET  | `/api/tables/{token}` | customer | Check the scanned table QR |
| POST | `/api/orders/quote` | customer | Calculate totals for a cart |
| POST | `/api/orders` | customer | Create an order (returns Stripe `client_secret` for card) |
| GET  | `/api/orders/{public_id}` | customer | Order status |
| POST | `/api/webhooks/stripe` | Stripe | Payment succeeded/failed |
| GET  | `/api/admin/orders` | staff | Active orders |
| PATCH | `/api/admin/orders/{id}/status` | staff | preparing / ready / completed / cancelled |
| POST | `/api/admin/orders/{id}/dispatch` | staff | Re-send to the other system |
| PATCH | `/api/admin/menu-items/{id}` | staff | Mark an item sold out |
| GET/POST | `/api/admin/tables` | staff | List / add tables |
| GET  | `/api/admin/tables/{id}/qr.png` | staff | Table QR code |
| GET  | `/api/admin/takeaway-qr.png` | staff | Takeaway QR code |

Staff endpoints need the `X-Admin-Key` header.

## Before going live

- Serve everything over **HTTPS** (Stripe requires it), with the frontend and API on your real domain. Set `FRONTEND_URL` to that domain **before** printing QR codes.
- Use a long random `ADMIN_API_KEY`. For several staff members, replace it with proper staff logins.
- Use [Alembic](https://alembic.sqlalchemy.org) migrations once you have real data. `seed.py` only creates missing tables; it doesn't alter existing ones.
- Edit the menu straight in MySQL for now (`categories`, `menu_items`, `item_options`), or add a menu editor to the staff page.
