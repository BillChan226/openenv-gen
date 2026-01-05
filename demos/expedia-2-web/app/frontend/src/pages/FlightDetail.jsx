import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Container from '../components/ui/Container';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import Price from '../components/results/Price';
import { getFlightById } from '../services/api';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../components/ui/Toast';

function timePart(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export default function FlightDetail() {
  const { flightId } = useParams();
  const [loading, setLoading] = useState(false);
  const [flight, setFlight] = useState(null);
  const [error, setError] = useState('');
  const cart = useCart();
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const f = await getFlightById(flightId);
        if (!cancelled) setFlight(f);
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load flight');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [flightId]);

  return (
    <Container className="py-8">
      <div className="mb-4 text-sm text-slate-600">
        <Link to="/flights" className="font-semibold text-brand-700 hover:underline">
          ← Back to results
        </Link>
      </div>

      {error ? <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

      {loading || !flight ? (
        <div className="grid place-items-center rounded-2xl border border-slate-200 bg-white p-10">
          <Spinner />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-xs font-black text-brand-700">Flight details</div>
                  <div className="mt-1 text-2xl font-black text-slate-900">
                    {flight.airline || 'Airline'} {flight.flight_no ? `• ${flight.flight_no}` : ''}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {flight.refundable ? <Badge variant="success">Refundable</Badge> : <Badge>Non-refundable</Badge>}
                    {flight.stops === 0 ? <Badge variant="blue">Nonstop</Badge> : null}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">Per traveler</div>
                  <div className="text-2xl font-black text-slate-900">
                    <Price cents={flight.price_cents} />
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs font-black text-slate-700">Departure</div>
                  <div className="mt-1 text-sm font-bold text-slate-900">
                    {flight.from_code || flight.origin_code} → {flight.to_code || flight.destination_code}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">{timePart(flight.depart_at || flight.depart_time)}</div>
                </div>
                <div>
                  <div className="text-xs font-black text-slate-700">Arrival</div>
                  <div className="mt-1 text-sm font-bold text-slate-900">{flight.to_code || flight.destination_code}</div>
                  <div className="mt-1 text-sm text-slate-600">{timePart(flight.arrive_at || flight.arrive_time)}</div>
                </div>
              </div>

              <div className="mt-6 text-sm text-slate-600">
                {flight.duration_minutes ? <div>Duration: <span className="font-semibold text-slate-900">{flight.duration_minutes} min</span></div> : null}
                {flight.cabin ? <div>Cabin: <span className="font-semibold text-slate-900">{flight.cabin}</span></div> : null}
              </div>
            </Card>
          </div>

          <div className="lg:col-span-4">
            <Card className="p-6">
              <div className="text-sm font-black text-slate-900">Add to cart</div>
              <div className="mt-2 text-sm text-slate-600">Checkout when you’re ready.</div>
              <Button
                type="button"
                className="mt-6 w-full"
                onClick={async () => {
                  try {
                    // UI-friendly payload (CartContext maps this to API payload)
                    await cart.addItem({ type: 'flight', id: flight.id || flightId, passengers: 1 });
                    toast.success('Added flight to cart');
                  } catch (e) {
                    toast.error(e?.response?.data?.error?.message || e?.message || 'Failed to add to cart');
                  }
                }}
              >
                Add flight
              </Button>
              <Button variant="secondary" className="mt-3 w-full" asChild>
                <Link to="/cart">Go to cart</Link>
              </Button>
            </Card>
          </div>
        </div>
      )}
    </Container>
  );
}
