import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';

import Button from '../components/ui/Button.jsx';
import Chip from '../components/ui/Chip.jsx';
import ItemDetailModal from '../components/menu/ItemDetailModal.jsx';
import ProductCard from '../components/menu/ProductCard.jsx';

import { getRestaurant, listRestaurantProducts } from '../services/api.js';

// NOTE: This page is reused for the spec route /restaurants/:restaurantId.
// We accept either param name (storeId or restaurantId) for backwards compatibility.
import { useCart } from '../contexts/CartContext.jsx';

export function Store() {
  const params = useParams();
  const storeId = params.storeId || params.restaurantId;
  const { addItem } = useCart();

  const [store, setStore] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const s = await getRestaurant(storeId);
        const p = await listRestaurantProducts(storeId, { limit: 100, offset: 0 });
        if (!mounted) return;
        setStore(s);
        const menu = p?.menu || p;
        const items = menu?.items || menu?.products || menu?.menuItems || [];
        setProducts(items);
      } catch (e) {
        if (mounted) setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [storeId]);

  const grouped = useMemo(() => {
    const map = new Map();
    for (const prod of products) {
      const cat = prod?.category || prod?.category_name || 'Popular items';
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat).push(prod);
    }
    return Array.from(map.entries());
  }, [products]);

  if (loading) {
    return (
      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4 text-sm text-zinc-600">Loading…</div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
        <div className="text-sm font-extrabold text-zinc-900">Could not load store</div>
        <div className="mt-1 text-sm text-zinc-600">{error?.message || 'Please try again.'}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-white shadow-sm ring-1 ring-zinc-200 overflow-hidden">
        <div className="h-40 sm:h-48 bg-gradient-to-br from-zinc-200 to-zinc-100" />
        <div className="p-4 sm:p-5">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <h1 className="text-2xl font-black tracking-tight text-zinc-900">{store?.name || 'Store'}</h1>
              <div className="mt-1 text-sm text-zinc-600">
                {store?.cuisine || 'Fast delivery'} · {store?.delivery_time_minutes || 30}–{(store?.delivery_time_minutes || 30) + 10} min
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Chip variant="good">DashPass eligible</Chip>
                <Chip>Group order</Chip>
                <Chip>Pickup</Chip>
              </div>
            </div>

            <Button variant="secondary" className="self-start">
              Start group order
            </Button>
          </div>
        </div>
      </div>

      {grouped.map(([cat, items]) => (
        <section key={cat} className="space-y-3">
          <div className="flex items-end justify-between">
            <h2 className="text-lg font-extrabold tracking-tight text-zinc-900">{cat}</h2>
            <div className="text-xs text-zinc-500">{items.length} items</div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((p) => (
              <ProductCard key={p.id} product={p} onClick={() => setSelected(p)} />
            ))}
          </div>
        </section>
      ))}

      <ItemDetailModal
        open={!!selected}
        product={selected}
        onClose={() => setSelected(null)}
        onAdd={async (product, qty) => {
          try {
            await addItem({ restaurantId: storeId, menuItemId: product.id || product.menuItemId || product.menu_item_id, quantity: qty });
            toast.success('Added to cart');
            setSelected(null);
          } catch (e) {
            if (e?.status === 409 || e?.code === 'CART_RESTAURANT_MISMATCH') {
              toast.error('Your cart has items from another store. Open cart to clear it.');
            } else {
              toast.error(e?.message || 'Could not add item');
            }
          }
        }}
      />
    </div>
  );
}

export default Store;
