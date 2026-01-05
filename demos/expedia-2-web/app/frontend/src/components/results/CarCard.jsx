import React from 'react';
import { Link } from 'react-router-dom';
import { Gauge, Users } from 'lucide-react';
import Card from '../ui/Card';
import Price from './Price';

export function CarCard({ car }) {
  const id = car?.id;
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <Link to={`/cars/${id}`} className="text-base font-black text-slate-900 hover:underline">
            {car?.make} {car?.model}
          </Link>
          <div className="mt-1 text-sm text-slate-600">{car?.category || 'Standard'} • {car?.company || 'Rental partner'}</div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1"><Users className="h-4 w-4" /> {car?.seats || 5} seats</span>
            <span className="inline-flex items-center gap-1"><Gauge className="h-4 w-4" /> {car?.transmission || 'Auto'}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-500">Per day</div>
          <div className="text-xl font-black text-slate-900">
            <Price cents={car?.price_per_day_cents || car?.price_cents} />
          </div>
          <Link
            to={`/cars/${id}`}
            className="mt-2 inline-flex rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600"
          >
            View
          </Link>
        </div>
      </div>
    </Card>
  );
}

export default CarCard;
