import React, { useEffect, useMemo, useState } from 'react';
import { MapPin } from 'lucide-react';
import Input from '../ui/Input';
import { searchLocations } from '../../services/api';

export function LocationInput({ label, value, onChange, placeholder = 'Where to?' }) {
  const [query, setQuery] = useState(value?.name || '');
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setQuery(value?.name || '');
  }, [value?.name]);

  const debounced = useMemo(() => query.trim(), [query]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!open || debounced.length < 2) {
        setItems([]);
        return;
      }
      setLoading(true);
      try {
        const res = await searchLocations({ q: debounced, limit: 8 });
        if (!cancelled) setItems(res);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    const t = window.setTimeout(run, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [debounced, open]);

  return (
    <div className="relative">
      <div className="mb-1 text-xs font-bold text-slate-700">{label}</div>
      <div className="relative">
        <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          placeholder={placeholder}
          className="pl-9"
        />
      </div>

      {open ? (
        <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="max-h-64 overflow-auto p-1">
            {loading ? <div className="p-3 text-sm text-slate-500">Searching…</div> : null}
            {!loading && items.length === 0 ? (
              <div className="p-3 text-sm text-slate-500">Type to search locations.</div>
            ) : null}
            {items.map((it) => (
              <button
                key={it.id || `${it.type}-${it.code}-${it.name}`}
                className="flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left hover:bg-slate-50"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange?.(it);
                  setQuery(it.name);
                  setOpen(false);
                }}
              >
                <div className="mt-0.5 h-7 w-7 rounded-lg bg-brand-50 text-brand-700 ring-1 ring-brand-100 grid place-items-center text-xs font-black">
                  {String(it.type || 'LOC').slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold text-slate-900">{it.name}</div>
                  <div className="truncate text-xs text-slate-500">
                    {it.region ? `${it.region} • ` : ''}
                    {it.country || ''}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default LocationInput;
