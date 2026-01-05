import React, { useEffect, useMemo, useState } from 'react';
import { cancelTrip, getTripById, getTrips } from '../services/api';
import TripCard from '../components/trips/TripCard';
import { Modal } from '../components/ui/Modal';
import Button from '../components/ui/Button';

export default function TripsPage() {
  const [tab, setTab] = useState('upcoming');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selected, setSelected] = useState(null);
  const [details, setDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const filtered = useMemo(() => {
    const now = new Date();
    return (items || []).filter((t) => {
      const start = t?.start_date ? new Date(t.start_date) : null;
      if (!start || Number.isNaN(start.getTime())) return tab === 'upcoming';
      return tab === 'upcoming' ? start >= now : start < now;
    });
  }, [items, tab]);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTrips({ limit: 50, offset: 0 });
      setItems(res || []);
    } catch (e) {
      setError(e?.response?.data?.error?.message || 'Failed to load trips.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onView = async (order) => {
    setSelected(order);
    setDetails(null);
    setDetailsLoading(true);
    try {
      const d = await getTripById(order.id);
      setDetails(d);
    } catch (e) {
      setDetails({ error: e?.response?.data?.error?.message || 'Failed to load details.' });
    } finally {
      setDetailsLoading(false);
    }
  };

  const onCancel = async (order) => {
    setError(null);
    try {
      await cancelTrip(order.id);
      await refresh();
    } catch (e) {
      setError(e?.response?.data?.error?.message || 'Unable to cancel trip.');
    }
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <h1 className="text-2xl font-extrabold text-slate-900">Trips</h1>
        <p className="mt-1 text-sm text-slate-600">Manage upcoming bookings and view past travel.</p>

        <div className="mt-5 flex gap-2">
          <button
            onClick={() => setTab('upcoming')}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
              tab === 'upcoming'
                ? 'border-blue-600 bg-blue-50 text-blue-700'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            Upcoming
          </button>
          <button
            onClick={() => setTab('past')}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
              tab === 'past'
                ? 'border-blue-600 bg-blue-50 text-blue-700'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            Past
          </button>
          <Button variant="secondary" className="ml-auto" onClick={refresh}>
            Refresh
          </Button>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        ) : null}

        <div className="mt-6 space-y-4">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div key={idx} className="h-28 animate-pulse rounded-2xl bg-white shadow-sm" />
              ))}
            </div>
          ) : filtered.length ? (
            filtered.map((o) => <TripCard key={o.id} order={o} onView={onView} onCancel={onCancel} />)
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <div className="text-lg font-bold text-slate-900">No trips found</div>
              <div className="mt-2 text-sm text-slate-600">When you book, your itinerary will appear here.</div>
            </div>
          )}
        </div>

        <Modal open={Boolean(selected)} title="Trip details" onClose={() => setSelected(null)}>
          {detailsLoading ? (
            <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
          ) : details?.error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{details.error}</div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-slate-700">
                <span className="font-semibold text-slate-900">Status:</span> {details?.status || selected?.status}
              </div>
              <pre className="max-h-72 overflow-auto rounded-xl bg-slate-50 p-4 text-xs text-slate-700">
                {JSON.stringify(details || selected, null, 2)}
              </pre>
              <div className="flex justify-end">
                <Button variant="secondary" onClick={() => setSelected(null)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
}
