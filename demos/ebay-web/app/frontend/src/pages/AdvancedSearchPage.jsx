import { useMemo, useState } from 'react';
import { advancedSearch } from '../services/api.js';
import { Spinner } from '../components/ui/Spinner.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { EmptyState } from '../components/ui/EmptyState.jsx';
import { Button } from '../components/ui/Button.jsx';

function formatPrice(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value ?? '');
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(n);
}

export default function AdvancedSearchPage() {
  const [form, setForm] = useState({
    name: '',
    sku: '',
    minPrice: '',
    maxPrice: '',
    sort: 'relevance'
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);

  const items = useMemo(() => {
    const list = data?.items;
    return Array.isArray(list) ? list : [];
  }, [data]);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload = {
        name: form.name.trim() || undefined,
        sku: form.sku.trim() || undefined,
        minPrice: form.minPrice !== '' ? Number(form.minPrice) : undefined,
        maxPrice: form.maxPrice !== '' ? Number(form.maxPrice) : undefined,
        sort: form.sort || undefined,
        limit: 50,
        offset: 0
      };
      const res = await advancedSearch(payload);
      setData(res);
    } catch (e2) {
      setError(e2?.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-page py-8" data-testid="advanced-search-page">
      <h1 className="text-2xl font-bold text-slate-900">Advanced search</h1>
      <p className="mt-1 text-sm text-slate-600">Search by name, SKU, and price range.</p>

      <form className="mt-6 grid grid-cols-1 gap-4 rounded-lg border bg-white p-4 sm:grid-cols-2" onSubmit={onSubmit}>
        <label className="block">
          <div className="text-sm font-medium text-slate-700">Name</div>
          <input
            value={form.name}
            onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            placeholder="e.g. iPhone"
            data-testid="adv-name"
          />
        </label>

        <label className="block">
          <div className="text-sm font-medium text-slate-700">SKU</div>
          <input
            value={form.sku}
            onChange={(e) => setForm((s) => ({ ...s, sku: e.target.value }))}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            placeholder="e.g. SKU-123"
            data-testid="adv-sku"
          />
        </label>

        <label className="block">
          <div className="text-sm font-medium text-slate-700">Min price</div>
          <input
            value={form.minPrice}
            onChange={(e) => setForm((s) => ({ ...s, minPrice: e.target.value }))}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            placeholder="0"
            inputMode="decimal"
            data-testid="adv-min-price"
          />
        </label>

        <label className="block">
          <div className="text-sm font-medium text-slate-700">Max price</div>
          <input
            value={form.maxPrice}
            onChange={(e) => setForm((s) => ({ ...s, maxPrice: e.target.value }))}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            placeholder="1000"
            inputMode="decimal"
            data-testid="adv-max-price"
          />
        </label>

        <label className="block sm:col-span-2">
          <div className="text-sm font-medium text-slate-700">Sort</div>
          <select
            value={form.sort}
            onChange={(e) => setForm((s) => ({ ...s, sort: e.target.value }))}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            data-testid="adv-sort"
          >
            <option value="relevance">Relevance</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="position">Category position</option>
          </select>
        </label>

        <div className="sm:col-span-2 flex items-center justify-end gap-2">
          <Button type="submit" disabled={loading} data-testid="adv-submit">
            {loading ? 'Searching…' : 'Search'}
          </Button>
        </div>
      </form>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner />
          </div>
        ) : error ? (
          <Alert variant="error">{error}</Alert>
        ) : data && items.length === 0 ? (
          <EmptyState title="No results" description="Try adjusting your filters." data-testid="adv-empty" />
        ) : items.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((p) => (
              <div key={p.id || p.sku} className="rounded-lg border bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-900">{p?.name}</div>
                    <div className="mt-1 text-xs text-slate-500">SKU: {p?.sku || '—'}</div>
                  </div>
                  <div className="text-sm font-semibold text-slate-900">{formatPrice(p?.price)}</div>
                </div>
                {p?.shortDescription ? (
                  <p className="mt-3 line-clamp-3 text-sm text-slate-700">{p.shortDescription}</p>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
