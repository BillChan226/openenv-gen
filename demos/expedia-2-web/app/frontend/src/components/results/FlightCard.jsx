import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Price from './Price';

function timePart(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function FlightCard({ flight }) {
  const id = flight?.id;
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/flights/${id}`} className="text-base font-black text-slate-900 hover:underline">
              {flight?.airline || 'Airline'} {flight?.flight_no ? `• ${flight.flight_no}` : ''}
            </Link>
            {flight?.refundable ? <Badge variant="success">Refundable</Badge> : null}
            {flight?.stops === 0 ? <Badge variant="blue">Nonstop</Badge> : null}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-700">
            <div className="font-bold">{flight?.from_code || flight?.origin_code}</div>
            <div className="text-slate-400">
              <ArrowRight className="h-4 w-4" />
            </div>
            <div className="font-bold">{flight?.to_code || flight?.destination_code}</div>
            <div className="text-slate-400">•</div>
            <div>
              {timePart(flight?.depart_at || flight?.depart_time)} – {timePart(flight?.arrive_at || flight?.arrive_time)}
            </div>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {flight?.duration_minutes ? `${flight.duration_minutes} min` : ''}
            {flight?.stops !== undefined ? ` • ${flight.stops} stop${flight.stops === 1 ? '' : 's'}` : ''}
          </div>
        </div>

        <div className="flex items-end justify-between gap-4 md:flex-col md:items-end">
          <div className="text-right">
            <div className="text-xs text-slate-500">Per traveler</div>
            <div className="text-xl font-black text-slate-900">
              <Price cents={flight?.price_cents} />
            </div>
          </div>
          <Link
            to={`/flights/${id}`}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-brand-600"
          >
            View deal
          </Link>
        </div>
      </div>
    </Card>
  );
}

export default FlightCard;
