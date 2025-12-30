import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../contexts/CartContext.jsx';
import { Spinner } from '../components/ui/Spinner.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { EmptyState } from '../components/ui/EmptyState.jsx';
import { Button } from '../components/ui/Button.jsx';

function formatPrice(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value ?? '');
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(n);
}

export default function CartPage() {
  const { cart, loading, error, refresh, setQuantity, removeItem, clearError } = useCart();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const items = Array.isArray(cart?.items) ? cart.items : [];

  const subtotal = cart?.subtotal ?? items.reduce((sum, i) => sum + Number(i?.product?.price || 0) * Number(i?.quantity || 0), 0);

  return (
    <div className="container-page py-8" data-testid="cart-page">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Cart</h1>
          <p className="mt-1 text-sm text-slate-600">Review items before checkout.</p>
        </div>
        <Link to="/" className="text-sm font-medium text-blue-700 hover:underline" data-testid="cart-continue-shopping">
          Continue shopping
        </Link>
      </div>

      {error ? (
        <div className="mt-4">
          <Alert variant="error" onClose={clearError}>
            {error}
          </Alert>
        </div>
      ) : null}

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner />
          </div>
        ) : items.length === 0 ? (
          <EmptyState title="Your cart is empty" description="Add items from the home page." data-testid="cart-empty" />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-3">
              {items.map((i) => (
                <div key={i.productId} className="rounded-lg border bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-900">{i?.product?.name || i.productId}</div>
                      <div className="mt-1 text-xs text-slate-500">SKU: {i?.product?.sku || '—'}</div>
                    </div>
                    <div className="text-sm font-semibold text-slate-900">{formatPrice(i?.product?.price)}</div>
                  </div>

                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      Qty
                      <input
                        type="number"
                        min={0}
                        value={i.quantity}
                        onChange={(e) => setQuantity(i.productId, Number(e.target.value))}
                        className="w-24 rounded-lg border px-3 py-2 text-sm focus-ring"
                        data-testid={`cart-qty-${i.productId}`}
                      />
                    </label>

                    <Button
                      variant="secondary"
                      onClick={() => removeItem(i.productId)}
                      data-testid={`cart-remove-${i.productId}`}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-900">Order summary</div>
              <div className="mt-3 flex items-center justify-between text-sm text-slate-700">
                <span>Subtotal</span>
                <span className="font-semibold text-slate-900">{formatPrice(subtotal)}</span>
              </div>
              <div className="mt-4">
                <Button className="w-full" disabled data-testid="cart-checkout">
                  Checkout (demo)
                </Button>
                <p className="mt-2 text-xs text-slate-500">Checkout is disabled in this demo.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
