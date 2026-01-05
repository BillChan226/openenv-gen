import React, { useEffect, useState } from 'react';

import { listOrders } from '../services/api.js';
import Price from '../components/ui/Price.jsx';

export function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const data = await listOrders({ limit: 20, offset: 0 });
        if (mounted) setOrders(data?.items || data || []);
      } catch (e) {
        if (mounted) setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
        <div className="text-lg font-extrabold tracking-tight text-zinc-900">Orders</div>
        <div className="mt-1 text-sm text-zinc-600">Your recent orders</div>
      </div>

      {loading ? (
        <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4 text-sm text-zinc-600">Loading…</div>
      ) : error ? (
        <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
          <div className="text-sm font-extrabold text-zinc-900">Could not load orders</div>
          <div className="mt-1 text-sm text-zinc-600">{error?.message || 'Please try again.'}</div>
        </div>
      ) : orders.length === 0 ? (
        <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-6 text-center">
          <div className="text-sm font-extrabold text-zinc-900">No orders yet</div>
          <div className="mt-1 text-sm text-zinc-600">Place an order and it will show up here.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {orders.map((o) => (
            <div key={o.id} className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-extrabold text-zinc-900">Order #{o.id}</div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {o.restaurant_name || 'Restaurant'} · {o.status || 'placed'}
                  </div>
                </div>
                <div className="text-sm font-extrabold text-zinc-900">
                  <Price cents={o.total_cents ?? 0} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Orders;
