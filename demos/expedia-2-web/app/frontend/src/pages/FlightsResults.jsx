import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Container from '../components/ui/Container';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import FlightCard from '../components/results/FlightCard';
import { searchFlights } from '../services/api';

export default function FlightsResults() {
  const [sp, setSp] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');

  const params = useMemo(() => Object.fromEntries(sp.entries()), [sp]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const res = await searchFlights({ ...params, page: params.page || 1, limit: params.limit || 20 });
        if (!cancelled) setItems(res.items || res);
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load flights');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [params]);

  return (
    <Container className="py-8">
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Card className="p-4">
            <div className="text-sm font-black text-slate-900">Filters</div>
            <div className="mt-4 grid gap-3">
              <div>
                <div className="mb-1 text-xs font-bold text-slate-700">Max price (USD)</div>
                <Input
                  type="number"
                  value={params.max_price_cents ? Number(params.max_price_cents) / 100 : ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    const next = new URLSearchParams(sp);
                    if (!v) next.delete('max_price_cents');
                    else next.set('max_price_cents', String(Math.round(Number(v) * 100)));
                    setSp(next, { replace: true });
                  }}
                />
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  const next = new URLSearchParams(sp);
                  next.delete('page');
                  setSp(next, { replace: true });
                }}
              >
                Apply
              </Button>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-8">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <div className="text-xl font-black text-slate-900">Flight deals</div>
              <div className="text-sm text-slate-600">Pick a flight, then add to cart.</div>
            </div>
          </div>

          {error ? <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

          {loading ? (
            <div className="grid place-items-center rounded-2xl border border-slate-200 bg-white p-10">
              <Spinner />
            </div>
          ) : (
            <div className="grid gap-4">
              {items.map((f) => (
                <FlightCard key={f.id} flight={f} />
              ))}
              {items.length === 0 ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600">
                  No flights found. Try adjusting your dates or destination.
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </Container>
  );
}
