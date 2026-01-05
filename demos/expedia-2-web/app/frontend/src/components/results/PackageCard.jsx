import React from 'react';
import { Link } from 'react-router-dom';
import { Plane, Hotel } from 'lucide-react';
import Card from '../ui/Card';
import Price from './Price';

export function PackageCard({ pkg }) {
  const id = pkg?.id;
  return (
    <Card className="overflow-hidden">
      <div className="grid grid-cols-12">
        <div className="col-span-12 h-44 bg-slate-100 sm:col-span-4 sm:h-full">
          {pkg?.image_url ? (
            <img src={pkg.image_url} alt={pkg.name} className="h-full w-full object-cover" />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-brand-50 to-slate-100" />
          )}
        </div>
        <div className="col-span-12 p-4 sm:col-span-8">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link to={`/packages/${id}`} className="block truncate text-base font-black text-slate-900 hover:underline">
                {pkg?.name || 'Vacation package'}
              </Link>
              <div className="mt-1 text-sm text-slate-600">{pkg?.to_name || pkg?.destination_name || ''}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1">
                  <Plane className="h-4 w-4" /> Flight included
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1">
                  <Hotel className="h-4 w-4" /> Hotel included
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Bundle price</div>
              <div className="text-xl font-black text-slate-900">
                <Price cents={pkg?.total_price_cents || pkg?.price_cents} />
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-end">
            <Link
              to={`/packages/${id}`}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-brand-600"
            >
              View
            </Link>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default PackageCard;
