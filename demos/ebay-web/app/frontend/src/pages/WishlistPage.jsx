import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useWishlist } from '../contexts/WishlistContext.jsx';
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

export default function WishlistPage() {
  const { wishlist, loading, error, refresh, remove, clearError } = useWishlist();
  const { addItem } = useCart();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const items = Array.isArray(wishlist?.items) ? wishlist.items : [];

  return (
    <div className="container-page py-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Wishlist</h1>
          <p className="mt-1 text-sm text-slate-600">Saved items you may want later.</p>
        </div>
        <Link to="/" className="text-sm font-medium text-blue-700 hover:underline" data-testid="wishlist-back-home">
          Back to home
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
          <EmptyState title="No saved items" description="Browse products and add them to your wishlist." data-testid="wishlist-empty" />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((i) => {
              const p = i.product || i;
              const id = i.productId || p.id;
              return (
                <div key={id} className="rounded-lg border bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-900">{p?.name || id}</div>
                      <div className="mt-1 text-xs text-slate-500">SKU: {p?.sku || '—'}</div>
                    </div>
                    <div className="text-sm font-semibold text-slate-900">{formatPrice(p?.price)}</div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => remove(id)}
                      data-testid={`wishlist-remove-${id}`}
                    >
                      Remove
                    </Button>
                    <Button
                      onClick={() => addItem(p, 1)}
                      data-testid={`wishlist-add-to-cart-${id}`}
                    >
                      Add to cart
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
