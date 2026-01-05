import React from 'react';
import { Input } from '../ui/Input';

export default function FilterSidebar({ filters = {}, onChange, variant = 'hotels' }) {
  const set = (key, value) => onChange?.({ ...filters, [key]: value });

  return (
    <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-bold text-slate-900">Filters</div>
      <div className="mt-1 text-xs text-slate-600">Refine your results</div>

      <div className="mt-4 space-y-4">
        <Input
          label="Max price"
          type="number"
          value={filters.priceMax || ''}
          onChange={(e) => set('priceMax', e.target.value)}
          placeholder="e.g. 300"
        />

        {variant === 'flights' ? (
          <Input
            label="Max stops"
            type="number"
            value={filters.stopsMax || ''}
            onChange={(e) => set('stopsMax', e.target.value)}
            placeholder="0, 1, 2"
          />
        ) : null}

        {variant === 'hotels' ? (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-800">Star rating</label>
            <div className="flex flex-wrap gap-2">
              {[5, 4, 3, 2].map((n) => {
                const active = String(filters.stars) === String(n);
                return (
                  <button
                    key={n}
                    type="button"
                    onClick={() => set('stars', active ? '' : String(n))}
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                      active
                        ? 'border-blue-600 bg-blue-50 text-blue-700'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {n}+
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {variant === 'cars' ? (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-800">Car type</label>
            <select
              value={filters.type || ''}
              onChange={(e) => set('type', e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
            >
              <option value="">Any</option>
              <option value="economy">Economy</option>
              <option value="standard">Standard</option>
              <option value="suv">SUV</option>
              <option value="luxury">Luxury</option>
            </select>
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => onChange?.({})}
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Clear filters
        </button>
      </div>
    </aside>
  );
}
