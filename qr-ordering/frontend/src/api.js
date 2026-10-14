const BASE = import.meta.env.VITE_API_URL || '';

async function request(path, { method = 'GET', body, headers = {} } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === 'string') message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(', ');
    } catch {
      // keep the generic message
    }
    throw new Error(message);
  }
  return res.headers.get('content-type')?.includes('application/json') ? res.json() : res.blob();
}

export const api = {
  menu: () => request('/api/menu'),
  table: (token) => request(`/api/tables/${encodeURIComponent(token)}`),
  quote: (cart) => request('/api/orders/quote', { method: 'POST', body: cart }),
  createOrder: (order) => request('/api/orders', { method: 'POST', body: order }),
  order: (publicId) => request(`/api/orders/${encodeURIComponent(publicId)}`),
};

export function staffApi(adminKey) {
  const headers = { 'X-Admin-Key': adminKey };
  return {
    orders: () => request('/api/admin/orders', { headers }),
    setStatus: (id, status) =>
      request(`/api/admin/orders/${id}/status`, { method: 'PATCH', body: { status }, headers }),
    resend: (id) => request(`/api/admin/orders/${id}/dispatch`, { method: 'POST', headers }),
    tables: () => request('/api/admin/tables', { headers }),
    addTable: (name) => request('/api/admin/tables', { method: 'POST', body: { name }, headers }),
    qrPng: (path) => request(path, { headers }),
  };
}
