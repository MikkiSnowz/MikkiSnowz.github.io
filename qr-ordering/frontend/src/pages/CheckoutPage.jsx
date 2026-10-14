import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { cartToApiItems, useCart } from '../cart.jsx';
import { formatMoney } from '../money.js';
import StripePayment from '../components/StripePayment.jsx';

export default function CheckoutPage() {
  const cart = useCart();
  const navigate = useNavigate();
  const [settings, setSettings] = useState(null);
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [payment, setPayment] = useState(null); // { publicId, clientSecret } once a card order exists
  const [form, setForm] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    notes: '',
    order_type: cart.table ? 'dine_in' : 'takeaway',
    payment_method: 'card',
  });

  const menuLink = cart.table ? `/t/${cart.table.token}` : '/takeaway';
  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  useEffect(() => {
    api.menu().then((m) => setSettings(m.settings)).catch((e) => setError(e.message));
  }, []);

  // Ask the server for the real total whenever the cart or payment method changes.
  useEffect(() => {
    if (cart.lines.length === 0) return;
    let cancelled = false;
    api
      .quote({ items: cartToApiItems(cart.lines), payment_method: form.payment_method })
      .then((q) => !cancelled && (setQuote(q), setError('')))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [cart.lines, form.payment_method]);

  if (cart.lines.length === 0 && !payment) {
    return (
      <main className="page narrow center">
        <p>Your order is empty.</p>
        <Link className="button" to={menuLink}>
          Back to menu
        </Link>
      </main>
    );
  }

  const currency = settings?.currency || 'aud';

  async function placeOrder(e) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const { order, stripe_client_secret } = await api.createOrder({
        items: cartToApiItems(cart.lines),
        table_token: cart.table?.token || null,
        order_type: form.order_type,
        payment_method: form.payment_method,
        customer_name: form.customer_name,
        customer_phone: form.customer_phone || null,
        customer_email: form.customer_email || null,
        notes: form.notes || null,
      });
      if (stripe_client_secret) {
        setPayment({ publicId: order.public_id, clientSecret: stripe_client_secret });
      } else {
        cart.clear();
        navigate(`/order/${order.public_id}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (payment) {
    return (
      <main className="page narrow">
        <h1>Payment</h1>
        <p className="total-line">
          Total <strong>{quote && formatMoney(quote.total_cents, currency)}</strong>
        </p>
        <StripePayment
          clientSecret={payment.clientSecret}
          returnUrl={`${window.location.origin}/order/${payment.publicId}`}
        />
      </main>
    );
  }

  return (
    <main className="page narrow">
      <Link to={menuLink} className="back">
        ← Menu
      </Link>
      <h1>Your order</h1>
      {cart.table && <p className="muted">{cart.table.name}</p>}

      <ul className="cart-lines">
        {cart.lines.map((l) => (
          <li key={l.key}>
            <div className="grow">
              <strong>{l.name}</strong>
              {l.options.length > 0 && <div className="muted small">{l.options.map((o) => o.name).join(', ')}</div>}
              {l.notes && <div className="muted small">“{l.notes}”</div>}
            </div>
            <div className="stepper small">
              <button type="button" onClick={() => cart.setQuantity(l.key, l.quantity - 1)} aria-label="Fewer">
                −
              </button>
              <span>{l.quantity}</span>
              <button type="button" onClick={() => cart.setQuantity(l.key, l.quantity + 1)} aria-label="More">
                +
              </button>
            </div>
            <span className="line-price">{formatMoney(l.unitPriceCents * l.quantity, currency)}</span>
          </li>
        ))}
      </ul>

      {quote && <Totals quote={quote} />}

      <form onSubmit={placeOrder} className="checkout-form">
        {cart.table && (
          <fieldset className="segmented">
            <legend>Order type</legend>
            {[
              ['dine_in', 'Dine in'],
              ['takeaway', 'Takeaway'],
            ].map(([value, label]) => (
              <label key={value}>
                <input
                  type="radio"
                  name="order_type"
                  value={value}
                  checked={form.order_type === value}
                  onChange={update('order_type')}
                />
                <span>{label}</span>
              </label>
            ))}
          </fieldset>
        )}

        <label className="field">
          <span>Name *</span>
          <input required maxLength={100} value={form.customer_name} onChange={update('customer_name')} />
        </label>
        <label className="field">
          <span>Phone</span>
          <input type="tel" maxLength={30} value={form.customer_phone} onChange={update('customer_phone')} />
        </label>
        <label className="field">
          <span>Email (for your receipt)</span>
          <input type="email" value={form.customer_email} onChange={update('customer_email')} />
        </label>
        <label className="field">
          <span>Notes for the kitchen</span>
          <textarea rows={2} maxLength={1000} value={form.notes} onChange={update('notes')} />
        </label>

        {settings?.allow_pay_at_counter && (
          <fieldset className="segmented">
            <legend>Payment</legend>
            {[
              ['card', 'Pay now by card'],
              ['counter', 'Pay at counter'],
            ].map(([value, label]) => (
              <label key={value}>
                <input
                  type="radio"
                  name="payment_method"
                  value={value}
                  checked={form.payment_method === value}
                  onChange={update('payment_method')}
                />
                <span>{label}</span>
              </label>
            ))}
          </fieldset>
        )}

        {error && <p className="error">{error}</p>}
        <button className="button full" disabled={submitting || !quote}>
          {submitting
            ? 'Placing order…'
            : form.payment_method === 'card'
              ? 'Continue to payment'
              : 'Place order'}
        </button>
      </form>
    </main>
  );
}

export function Totals({ quote }) {
  const c = quote.currency;
  return (
    <dl className="totals">
      <dt>Subtotal</dt>
      <dd>{formatMoney(quote.subtotal_cents, c)}</dd>
      {quote.surcharge_cents > 0 && (
        <>
          <dt>Card surcharge</dt>
          <dd>{formatMoney(quote.surcharge_cents, c)}</dd>
        </>
      )}
      {!quote.tax_inclusive && (
        <>
          <dt>Tax</dt>
          <dd>{formatMoney(quote.tax_cents, c)}</dd>
        </>
      )}
      <dt className="total">Total</dt>
      <dd className="total">{formatMoney(quote.total_cents, c)}</dd>
      {quote.tax_inclusive && quote.tax_cents > 0 && (
        <dd className="muted small full-row">Includes {formatMoney(quote.tax_cents, c)} tax</dd>
      )}
    </dl>
  );
}
