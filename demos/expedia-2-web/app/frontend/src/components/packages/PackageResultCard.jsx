import React from 'react';
import Button from '../ui/Button';
import { Badge } from '../ui/Badge';
import { formatMoney } from '../../utils/money';

export default function PackageResultCard({ pkg, onSelect }) {
  const title = pkg?.title || pkg?.name || 'Package';
  const subtitle = pkg?.subtitle || pkg?.route || pkg?.location;
  const image = pkg?.image_url || pkg?.imageUrl;
  const priceCents = pkg?.price_total_cents ?? pkg?.total_price_cents ?? pkg?.price_cents ?? 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-[180px_1fr]">
        <div className="h-32 w-full overflow-hidden rounded-xl bg-slate-100 sm:h-full">
          {image ? <img src={image} alt={title} className="h-full w-full object-cover" loading="lazy" /> : null}
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900">{title}</h3>
                {pkg?.deal ? <Badge variant="deal">Deal</Badge> : null}
              </div>
              {subtitle ? <div className="mt-1 text-sm text-slate-600">{subtitle}</div> : null}
              {pkg?.includes ? (
                <div className="mt-2 text-xs text-slate-600">Includes: {pkg.includes.join(', ')}</div>
              ) : null}
            </div>

            <div className="text-right">
              <div className="text-xs text-slate-500">Package price</div>
              <div className="text-xl font-extrabold text-slate-900">{formatMoney(priceCents)}</div>
              <div className="text-xs text-slate-500">per traveler</div>
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Button onClick={() => onSelect?.(pkg)} className="px-5">
              View package
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
