import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useCart } from '../cart.jsx';
import { formatMoney } from '../money.js';
import { Totals } from './CheckoutPage.jsx';

const STEPS = [
  ['placed', 'Order received'],
  ['preparing', 'Being prepared'],
  ['ready', 'Ready'],
  ['completed', 'Completed'],
];
const FINISHED = ['completed', 'cancelled'];

export default function OrderStatusPage() {
  const { publicId } = useParams();
  const cart = useCart();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let timer;
    let stopped = false;
    async function poll() {
      try {
        const o = await api.order(publicId);
        if (stopped) return;
        setOrder(o);
        setError('');
        if (FINISHED.includes(o.status)) return;
      } catch (e) {
        if (!stopped) setError(e.message);
      }
      timer = setTimeout(poll, 4000);
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [publicId]);

  // The order went through, so empty the cart (card orders land here after Stripe).
  const confirmed = order && order.status !== 'awaiting_payment';
  useEffect(() => {
    if (confirmed) cart.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmed]);

  if (error && !order) return <main className="page narrow center error">{error}</main>;
  if (!order) return <main className="page center">Loading…</main>;

  const stepIndex = STEPS.findIndex(([s]) => s === order.status);

  return (
    <main className="page narrow">
      <p className="muted center">Order number</p>
      <p className="order-number">{order.order_number}</p>

      {order.status === 'awaiting_payment' && (
        <p className="notice">
          {order.payment_status === 'failed'
            ? 'Your payment did not go through. Please try again or ask staff for help.'
            : 'Waiting for payment confirmation…'}
        </p>
      )}
      {order.status === 'cancelled' && <p className="error">This order was cancelled.</p>}
      {order.payment_method === 'counter' && order.payment_status === 'unpaid' && order.status !== 'cancelled' && (
        <p className="notice">Please pay {formatMoney(order.total_cents, order.currency)} at the counter.</p>
      )}

      {stepIndex >= 0 && (
        <ol className="steps">
          {STEPS.map(([status, label], i) => (
            <li key={status} className={i <= stepIndex ? 'done' : ''}>
              {label}
            </li>
          ))}
        </ol>
      )}

      <h2>
        {order.order_type === 'dine_in' ? `Dine in · ${order.table?.name}` : 'Takeaway'} · {order.customer_name}
      </h2>
      <ul className="cart-lines">
        {order.items.map((item, i) => (
          <li key={i}>
            <span>{item.quantity}×</span>
            <div className="grow">
              <strong>{item.name}</strong>
              {item.options.length > 0 && <div className="muted small">{item.options.map((o) => o.name).join(', ')}</div>}
              {item.notes && <div className="muted small">“{item.notes}”</div>}
            </div>
            <span className="line-price">{formatMoney(item.line_total_cents, order.currency)}</span>
          </li>
        ))}
      </ul>
      <Totals quote={order} />
    </main>
  );
}
