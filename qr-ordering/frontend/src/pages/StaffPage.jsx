import { useCallback, useEffect, useMemo, useState } from 'react';
import { staffApi } from '../api.js';
import { formatMoney } from '../money.js';

const KEY_STORAGE = 'qr-ordering-admin-key';
const NEXT_STATUS = { placed: 'preparing', preparing: 'ready', ready: 'completed' };
const NEXT_LABEL = { placed: 'Start preparing', preparing: 'Mark ready', ready: 'Complete' };

function readKey() {
  try {
    return localStorage.getItem(KEY_STORAGE) || '';
  } catch {
    return '';
  }
}

export default function StaffPage() {
  const [adminKey, setAdminKey] = useState(readKey);
  const [tab, setTab] = useState('orders');

  if (!adminKey) return <Login onLogin={setAdminKey} />;

  const logout = () => {
    try {
      localStorage.removeItem(KEY_STORAGE);
    } catch {
      // ignore
    }
    setAdminKey('');
  };

  return (
    <main className="page staff">
      <header className="staff-header">
        <nav className="segmented">
          <button className={tab === 'orders' ? 'active' : ''} onClick={() => setTab('orders')}>
            Orders
          </button>
          <button className={tab === 'tables' ? 'active' : ''} onClick={() => setTab('tables')}>
            Tables &amp; QR codes
          </button>
        </nav>
        <button className="link" onClick={logout}>
          Log out
        </button>
      </header>
      {tab === 'orders' ? <Orders adminKey={adminKey} onAuthError={logout} /> : <Tables adminKey={adminKey} />}
    </main>
  );
}

function Login({ onLogin }) {
  const [key, setKey] = useState('');
  return (
    <main className="page narrow">
      <h1>Staff login</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          try {
            localStorage.setItem(KEY_STORAGE, key);
          } catch {
            // only remembered for this visit
          }
          onLogin(key);
        }}
      >
        <label className="field">
          <span>Admin key</span>
          <input type="password" value={key} onChange={(e) => setKey(e.target.value)} required />
        </label>
        <button className="button full">Log in</button>
      </form>
    </main>
  );
}

function Orders({ adminKey, onAuthError }) {
  const client = useMemo(() => staffApi(adminKey), [adminKey]);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      setOrders(await client.orders());
      setError('');
    } catch (e) {
      if (/admin key/i.test(e.message)) onAuthError();
      else setError(e.message);
    }
  }, [client, onAuthError]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 10000);
    return () => clearInterval(timer);
  }, [refresh]);

  const act = (fn) => async () => {
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <>
      {error && <p className="error">{error}</p>}
      {orders.length === 0 && <p className="muted">No active orders.</p>}
      <div className="ticket-grid">
        {orders.map((o) => (
          <article key={o.id} className={`ticket status-${o.status}`}>
            <header>
              <strong>#{o.order_number}</strong>
              <span>{o.order_type === 'dine_in' ? o.table?.name : 'Takeaway'}</span>
              <span className="muted small">{new Date(o.created_at).toLocaleTimeString()}</span>
            </header>
            <div className="small">
              {o.customer_name}
              {o.customer_phone && ` · ${o.customer_phone}`}
            </div>
            <ul>
              {o.items.map((item, i) => (
                <li key={i}>
                  <strong>{item.quantity}×</strong> {item.name}
                  {item.options.length > 0 && <div className="muted small">{item.options.map((x) => x.name).join(', ')}</div>}
                  {item.notes && <div className="small">“{item.notes}”</div>}
                </li>
              ))}
            </ul>
            {o.notes && <p className="small notice">{o.notes}</p>}
            <div className="small">
              {formatMoney(o.total_cents, o.currency)} ·{' '}
              {o.payment_status === 'paid' ? 'Paid' : o.payment_method === 'counter' ? 'Pay at counter' : o.payment_status}
            </div>
            {o.dispatch_status === 'failed' && (
              <p className="error small">
                Not sent to POS: {o.dispatch_error}{' '}
                <button className="link" onClick={act(() => client.resend(o.id))}>
                  Retry
                </button>
              </p>
            )}
            <footer>
              {NEXT_STATUS[o.status] && (
                <button className="button" onClick={act(() => client.setStatus(o.id, NEXT_STATUS[o.status]))}>
                  {NEXT_LABEL[o.status]}
                </button>
              )}
              <button
                className="link danger"
                onClick={act(() => window.confirm(`Cancel order #${o.order_number}?`) && client.setStatus(o.id, 'cancelled'))}
              >
                Cancel
              </button>
            </footer>
          </article>
        ))}
      </div>
    </>
  );
}

function QrImage({ client, path, filename }) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let objectUrl;
    client
      .qrPng(path)
      .then((blob) => setUrl((objectUrl = URL.createObjectURL(blob))))
      .catch(() => setUrl(''));
    return () => objectUrl && URL.revokeObjectURL(objectUrl);
  }, [client, path]);
  if (!url) return <div className="qr placeholder" />;
  return (
    <a href={url} download={filename}>
      <img className="qr" src={url} alt={`QR code ${filename}`} />
    </a>
  );
}

function Tables({ adminKey }) {
  const client = useMemo(() => staffApi(adminKey), [adminKey]);
  const [tables, setTables] = useState([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const refresh = useCallback(() => client.tables().then(setTables).catch((e) => setError(e.message)), [client]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <>
      <p className="muted">Click a QR code to download it, then print it and stick it on the table.</p>
      {error && <p className="error">{error}</p>}
      <form
        className="inline-form"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await client.addTable(name);
            setName('');
            refresh();
          } catch (err) {
            setError(err.message);
          }
        }}
      >
        <input placeholder="New table name, e.g. Table 6" value={name} onChange={(e) => setName(e.target.value)} required />
        <button className="button">Add table</button>
      </form>
      <div className="qr-grid">
        <figure>
          <QrImage client={client} path="/api/admin/takeaway-qr.png" filename="takeaway-qr.png" />
          <figcaption>Takeaway / counter</figcaption>
        </figure>
        {tables.map((t) => (
          <figure key={t.id}>
            <QrImage client={client} path={t.qr_png_url} filename={`${t.name}-qr.png`} />
            <figcaption>
              {t.name}
              <br />
              <a className="small" href={t.order_url} target="_blank" rel="noreferrer">
                Open ordering page
              </a>
            </figcaption>
          </figure>
        ))}
      </div>
    </>
  );
}
