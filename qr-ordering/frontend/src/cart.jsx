import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const CartContext = createContext(null);
const STORAGE_KEY = 'qr-ordering-cart';

function load() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null;
  }
}

const EMPTY = { table: null, lines: [] };

export function CartProvider({ children }) {
  // Kept in sessionStorage so a page refresh (or the Stripe redirect) doesn't lose the cart.
  const [state, setState] = useState(() => load() || EMPTY);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // storage unavailable (private mode): the cart just won't survive a refresh
    }
  }, [state]);

  const value = useMemo(() => {
    // Estimate for the cart bar; the server calculates the real total at checkout.
    const estimateCents = state.lines.reduce((sum, l) => sum + l.unitPriceCents * l.quantity, 0);
    const count = state.lines.reduce((sum, l) => sum + l.quantity, 0);

    return {
      table: state.table,
      lines: state.lines,
      count,
      estimateCents,
      // table = { token, name } for dine-in, null for takeaway
      setTable: (table) =>
        setState((s) => (s.table?.token === table?.token ? s : { ...s, table })),
      add: (item, options, quantity, notes) =>
        setState((s) => {
          const optionIds = options.map((o) => o.id).sort((a, b) => a - b);
          const key = `${item.id}:${optionIds.join(',')}:${notes || ''}`;
          const existing = s.lines.find((l) => l.key === key);
          const lines = existing
            ? s.lines.map((l) => (l.key === key ? { ...l, quantity: l.quantity + quantity } : l))
            : [
                ...s.lines,
                {
                  key,
                  menuItemId: item.id,
                  name: item.name,
                  options,
                  optionIds,
                  notes,
                  quantity,
                  unitPriceCents: item.price_cents + options.reduce((sum, o) => sum + o.price_cents, 0),
                },
              ];
          return { ...s, lines };
        }),
      setQuantity: (key, quantity) =>
        setState((s) => ({
          ...s,
          lines:
            quantity <= 0
              ? s.lines.filter((l) => l.key !== key)
              : s.lines.map((l) => (l.key === key ? { ...l, quantity } : l)),
        })),
      clear: () => setState((s) => ({ ...s, lines: [] })),
    };
  }, [state]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}

export function cartToApiItems(lines) {
  return lines.map((l) => ({
    menu_item_id: l.menuItemId,
    quantity: l.quantity,
    option_ids: l.optionIds,
    notes: l.notes || null,
  }));
}
