import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import RestaurantCard from '../components/restaurants/RestaurantCard.jsx';
import SearchBar from '../components/layout/SearchBar.jsx';

import { listRestaurants } from '../services/api.js';

export function Goods() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const data = await listRestaurants({ q, limit: 24, offset: 0 });
        const list = data?.items || data || [];
        if (mounted) setItems(list);
      } catch (e) {
        if (mounted) setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [q]);

  const title = useMemo(() => (q ? `Results for “${q}”` : 'Browse goods'), [q]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
        <div className="text-lg font-extrabold tracking-tight text-zinc-900">{title}</div>
        <div className="mt-3">
          <SearchBar
            defaultValue={q}
            placeholder="Search stores"
            onSubmit={(next) => {
              setParams(next ? { q: next } : {});
            }}
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-[150px] rounded-2xl bg-white ring-1 ring-zinc-200 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
          <div className="text-sm font-extrabold text-zinc-900">Could not load stores</div>
          <div className="mt-1 text-sm text-zinc-600">{error?.message || 'Please try again.'}</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map((r) => (
            <RestaurantCard key={r.id} restaurant={r} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Goods;
