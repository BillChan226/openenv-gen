import React from 'react';
import { Users, Fuel, Gauge, Briefcase } from 'lucide-react';
import Button from '../ui/Button';
import { formatMoney } from '../../utils/money';

export default function CarResultCard({ car, onSelect }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-[160px_1fr]">
        <div className="h-28 w-full overflow-hidden rounded-xl bg-slate-100 sm:h-full">
          {car?.image_url || car?.imageUrl ? (
            <img
              src={car.image_url || car.imageUrl}
              alt={car?.name || 'Car'}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : null}
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">{car?.company || car?.vendor || 'Car rental'}</div>
              <div className="text-lg font-bold text-slate-900">{car?.name || car?.model || 'Standard'}</div>
              <div className="mt-1 text-sm text-slate-600">{car?.pickup_location || car?.pickupLocation}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Total</div>
              <div className="text-xl font-extrabold text-slate-900">
                {formatMoney(car?.price_total_cents ?? car?.total_price_cents ?? car?.price_cents ?? 0)}
              </div>
              <div className="text-xs text-slate-500">includes taxes & fees</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-4">
            <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
              <Users className="h-4 w-4 text-slate-500" />
              <span>{car?.seats || 5} seats</span>
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
              <Briefcase className="h-4 w-4 text-slate-500" />
              <span>{car?.bags || 2} bags</span>
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
              <Fuel className="h-4 w-4 text-slate-500" />
              <span>{car?.fuel || 'Gas'}</span>
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
              <Gauge className="h-4 w-4 text-slate-500" />
              <span>{car?.transmission || 'Auto'}</span>
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Button onClick={() => onSelect?.(car)} className="px-5">
              View deal
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
