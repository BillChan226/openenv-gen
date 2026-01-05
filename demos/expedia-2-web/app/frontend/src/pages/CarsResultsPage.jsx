import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { searchCars } from '../services/api';
import FilterSidebar from '../components/search/FilterSidebar';
import { SortSelect } from '../components/search/SortSelect';
import CarResultCard from '../components/cars/CarResultCard';

export default function CarsResultsPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();

  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState({ total: 0, limit: 20, offset: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [sort, setSort] = useState(params.get('sort') || 'price');
  const [filters, setFilters] = useState({ priceMax: params.get('priceMax') || '' });

  const query = useMemo(() => Object.fromEntries(params.entries()), [params]);

  useEffect(() => {
    let mounted = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const res = await searchCars({ ...query, sort, limit: query.limit || 20, offset: query.offset || 0 });
        // api.js returns list items only; meta must be read from raw response if needed.
        // For now, best-effort: keep items and infer total.
        if (!mounted) return;
        setItems(res || []);
        setMeta((m) => ({ ...m, total: Array.isArray(res) ? res.length : 0 }));
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.error?.message || 'Failed to load cars.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    run();
    return () => {
      mounted = false;
    };
  }, [query, sort]);

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900">Cars</h1>
            <p className="mt-1 text-sm text-slate-600">Compare rental cars from top providers.</p>
          </div>
          <SortSelect
            value={sort}
            onChange={setSort}
            options={[
              { value: 'price', label: 'Price (lowest)' },
              { value: 'rating', label: 'Rating' }
            ]}
          />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
          <FilterSidebar variant="cars" filters={filters} onChange={setFilters} />

          <div className="space-y-4">
            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                {error}
              </div>
            ) : null}

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, idx) => (
                  <div key={idx} className="h-28 animate-pulse rounded-2xl bg-white shadow-sm" />
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {items.map((car) => (
                  <CarResultCard key={car.id} car={car} onSelect={() => nav(`/cars/${car.id}`)} />
                ))}
                {!items.length ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm">
                    No cars found. Try adjusting your search.
                  </div>
                ) : null}
              </div>
            )}

            <div className="text-xs text-slate-500">Showing {items.length} results</div>
          </div>
        </div>
      </div>
    </div>
  );
}
