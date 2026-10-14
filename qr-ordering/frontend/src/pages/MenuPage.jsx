import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useCart } from '../cart.jsx';
import { formatMoney } from '../money.js';
import ItemModal from '../components/ItemModal.jsx';

export default function MenuPage() {
  const { tableToken } = useParams();
  const cart = useCart();
  const [menu, setMenu] = useState(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (!tableToken) {
      cart.setTable(null);
      return;
    }
    api
      .table(tableToken)
      .then((t) => cart.setTable({ token: tableToken, name: t.name }))
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableToken]);

  useEffect(() => {
    api.menu().then(setMenu).catch((e) => setError(e.message));
  }, []);

  const categories = useMemo(() => {
    if (!menu) return [];
    const q = search.trim().toLowerCase();
    return menu.categories
      .map((c) => ({
        ...c,
        items: c.items.filter(
          (i) => !q || i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q),
        ),
      }))
      .filter((c) => c.items.length > 0);
  }, [menu, search]);

  if (error) {
    return (
      <main className="page narrow center">
        <p className="error">{error}</p>
      </main>
    );
  }
  if (!menu) return <main className="page center">Loading menu…</main>;

  const currency = menu.settings.currency;

  return (
    <>
      <header className="topbar">
        <div>
          <strong>{menu.settings.business_name}</strong>
          <div className="muted small">{cart.table ? cart.table.name : 'Takeaway'}</div>
        </div>
      </header>

      <div className="sticky-nav">
        <input
          className="search"
          type="search"
          placeholder="Search products"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <nav className="category-tabs">
          {categories.map((c) => (
            <a key={c.id} href={`#cat-${c.id}`}>
              {c.name}
            </a>
          ))}
        </nav>
      </div>

      <main className="page with-cart-bar">
        {categories.map((c) => (
          <section key={c.id} id={`cat-${c.id}`} className="category">
            <h2>{c.name}</h2>
            {c.items.map((item) => (
              <button key={item.id} className="menu-item" onClick={() => setSelected(item)}>
                <div className="menu-item-text">
                  <h3>{item.name}</h3>
                  {item.description && <p className="muted small">{item.description}</p>}
                  <span className="price">{formatMoney(item.price_cents, currency)}</span>
                </div>
                {item.image_url && <img src={item.image_url} alt="" loading="lazy" />}
              </button>
            ))}
          </section>
        ))}
        {categories.length === 0 && <p className="muted center">No products match your search.</p>}
      </main>

      {cart.count > 0 && (
        <Link to="/checkout" className="cart-bar">
          <span className="badge">{cart.count}</span>
          <span>View order</span>
          <span>{formatMoney(cart.estimateCents, currency)}</span>
        </Link>
      )}

      {selected && (
        <ItemModal
          item={selected}
          currency={currency}
          onClose={() => setSelected(null)}
          onAdd={(options, quantity, notes) => {
            cart.add(selected, options, quantity, notes);
            setSelected(null);
          }}
        />
      )}
    </>
  );
}
