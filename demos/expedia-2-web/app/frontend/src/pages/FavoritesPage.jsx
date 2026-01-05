import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFavorites, removeFavorite } from '../services/api';
import Button from '../components/ui/Button';

export default function FavoritesPage() {
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFavorites();
      setItems(res || []);
    } catch (e) {
      setError(e?.response?.data?.error?.message || 'Failed to load favorites.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onRemove = async (favId) => {
    setError(null);
    try {
      await removeFavorite(favId);
      await refresh();
    } catch (e) {
      setError(e?.response?.data?.error?.message || 'Unable to remove favorite.');
    }
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900">Favorites</h1>
            <p className="mt-1 text-sm text-slate-600">Saved stays and deals for later.</p>
          </div>
          <Button variant="secondary" onClick={() => nav('/hotels')}>
            Browse stays
          </Button>
        </div>

        <div className="mt-6">
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
          ) : null}

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div key={idx} className="h-20 animate-pulse rounded-2xl bg-white shadow-sm" />
              ))}
            </div>
          ) : items.length ? (
            <div className="grid grid-cols-1 gap-3">
              {items.map((fav) => (
                <div
                  key={fav.id}
                  className="flex flex-col justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center"
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{fav.title || fav.name || 'Saved item'}</div>
                    <div className="mt-1 text-xs text-slate-600">Type: {fav.item_type || fav.type || '—'}</div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={() => onRemove(fav.id)}>
                      Remove
                    </Button>
                    <Button
                      onClick={() => {
                        if (fav.item_type === 'hotel' || fav.type === 'hotel') nav(`/hotels/${fav.item_id || fav.hotel_id}`);
                        else if (fav.item_type === 'flight' || fav.type === 'flight') nav(`/flights/${fav.item_id || fav.flight_id}`);
                        else nav('/');
                      }}
                    >
                      View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <div className="text-lg font-bold text-slate-900">No favorites yet</div>
              <div className="mt-2 text-sm text-slate-600">
                Browse hotels and tap the heart to save your favorite stays.
              </div>
              <Button className="mt-5" onClick={() => nav('/hotels')}>
                Find a stay
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
