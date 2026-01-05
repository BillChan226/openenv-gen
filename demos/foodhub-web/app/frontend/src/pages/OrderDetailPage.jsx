import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { getOrderById, reorder } from '../services/api';
import Button from '../components/ui/Button';
import Price from '../components/ui/Price';

export function OrderDetailPage() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reordering, setReordering] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        const data = await getOrderById(orderId);
        if (mounted) setOrder(data?.order || data);
      } catch (err) {
        toast.error(err?.response?.data?.error?.message || 'Failed to load order');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [orderId]);

  const doReorder = async () => {
    setReordering(true);
    try {
      await reorder(orderId);
      toast.success('Reordered! Cart updated.');
    } catch (err) {
      toast.error(err?.response?.data?.error?.message || 'Failed to reorder');
    } finally {
      setReordering(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="h-40 rounded-2xl border border-neutral-200 bg-white shadow-sm" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="text-sm text-neutral-700">Order not found.</div>
          <Link className="mt-3 inline-block text-sm font-semibold text-[#FF3008] hover:underline" to="/orders">
            Back to orders
          </Link>
        </div>
      </div>
    );
  }

  const items = order.items || [];
  const totalCents = order.totalCents ?? order.total_cents ?? 0;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-neutral-900">Order #{order.id}</h1>
          <div className="mt-1 text-sm text-neutral-600">Status: {order.status || '—'}</div>
        </div>
        <Button onClick={doReorder} disabled={reordering}>
          {reordering ? 'Reordering…' : 'Reorder'}
        </Button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-neutral-900">Items</h2>
          <div className="mt-4 space-y-3">
            {items.map((it) => (
              <div key={it.id} className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-neutral-900">{it.name}</div>
                  <div className="text-xs text-neutral-500">Qty {it.quantity}</div>
                </div>
                <Price cents={it.totalCents ?? it.total_cents ?? 0} className="text-sm font-semibold" />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm h-fit">
          <h2 className="text-sm font-bold text-neutral-900">Summary</h2>
          <div className="mt-4 flex items-center justify-between text-sm font-extrabold text-neutral-900">
            <span>Total</span>
            <Price cents={totalCents} />
          </div>
          <Link className="mt-4 inline-block text-sm font-semibold text-[#FF3008] hover:underline" to="/orders">
            Back to orders
          </Link>
        </div>
      </div>
    </div>
  );
}

export default OrderDetailPage;
