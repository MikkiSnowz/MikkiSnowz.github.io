import { useMemo, useState } from 'react';
import { formatMoney } from '../money.js';

export default function ItemModal({ item, currency, onClose, onAdd }) {
  const [chosen, setChosen] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState('');

  const groups = useMemo(() => {
    const map = new Map();
    for (const option of item.options) {
      if (!map.has(option.group_name)) map.set(option.group_name, []);
      map.get(option.group_name).push(option);
    }
    return [...map.entries()];
  }, [item]);

  const toggle = (option) =>
    setChosen((c) => (c.some((o) => o.id === option.id) ? c.filter((o) => o.id !== option.id) : [...c, option]));

  const unit = item.price_cents + chosen.reduce((sum, o) => sum + o.price_cents, 0);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        {item.image_url && <img className="modal-image" src={item.image_url} alt="" />}
        <h2>{item.name}</h2>
        {item.description && <p className="muted">{item.description}</p>}

        {groups.map(([group, options]) => (
          <fieldset key={group}>
            <legend>{group}</legend>
            {options.map((o) => (
              <label key={o.id} className="option">
                <input type="checkbox" checked={chosen.some((c) => c.id === o.id)} onChange={() => toggle(o)} />
                <span>{o.name}</span>
                {o.price_cents > 0 && <span className="muted">+{formatMoney(o.price_cents, currency)}</span>}
              </label>
            ))}
          </fieldset>
        ))}

        <label className="field">
          <span>Special requests</span>
          <input
            value={notes}
            maxLength={255}
            placeholder="e.g. no onion"
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>

        <div className="modal-actions">
          <div className="stepper">
            <button onClick={() => setQuantity((q) => Math.max(1, q - 1))} aria-label="Fewer">
              −
            </button>
            <span>{quantity}</span>
            <button onClick={() => setQuantity((q) => Math.min(50, q + 1))} aria-label="More">
              +
            </button>
          </div>
          <button className="button grow" onClick={() => onAdd(chosen, quantity, notes.trim())}>
            Add {formatMoney(unit * quantity, currency)}
          </button>
        </div>
      </div>
    </div>
  );
}
