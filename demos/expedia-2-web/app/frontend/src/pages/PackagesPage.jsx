import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { searchPackages } from '../services/api';
import PackageResultCard from '../components/packages/PackageResultCard';
import { SortSelect } from '../components/search/SortSelect';

export default function PackagesPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [sort, setSort] = useState(params.get('sort') || 'price');
  const query = useMemo(() => Object.fromEntries(params.entries()), [params]);

  useEffect(() => {
    let mounted = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const res = await searchPackages({ ...query, sort, limit: query.limit || 20, offset: query.offset || 0 });
        if (!mounted) return;
        setItems(res || []);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.error?.message || 'Failed to load packages.');
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
            <h1 className="text-2xl font-extrabold text-slate-900">Packages</h1>
            <p className="mt-1 text-sm text-slate-600">Bundle and save on flights + hotel.</p>
          </div>
          <SortSelect
            value={sort}
            onChange={setSort}
            options={[
              { value: 'price', label: 'Price (lowest)' },
              { value: 'popular', label: 'Most popular' }
            ]}
          />
        </div>

        <div className="mt-6 space-y-4">
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
          ) : null}

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div key={idx} className="h-28 animate-pulse rounded-2xl bg-white shadow-sm" />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {items.map((pkg) => (
                <PackageResultCard key={pkg.id} pkg={pkg} onSelect={() => nav(`/packages?selected=${pkg.id}`)} />
              ))}
              {!items.length ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm">
                  No packages found.
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
