import React from 'react';
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import StarRating from './StarRating';
import Price from './Price';

export function HotelCard({ hotel }) {
  const id = hotel?.id;
  return (
    <Card className="overflow-hidden">
      <div className="grid grid-cols-12">
        <div className="col-span-12 h-44 bg-slate-100 sm:col-span-4 sm:h-full">
          {hotel?.image_url ? (
            <img src={hotel.image_url} alt={hotel.name} className="h-full w-full object-cover" />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-brand-50 to-slate-100" />
          )}
        </div>
        <div className="col-span-12 p-4 sm:col-span-8">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link to={`/stays/${id}`} className="block truncate text-base font-black text-slate-900 hover:underline">
                {hotel?.name || 'Hotel'}
              </Link>
              <div className="mt-1 text-sm text-slate-600">{hotel?.neighborhood || hotel?.city || ''}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StarRating rating={hotel?.star_rating || hotel?.rating || 0} />
                {hotel?.refundable ? <Badge variant="success">Refundable</Badge> : null}
                {hotel?.deal ? <Badge variant="gold">Member deal</Badge> : null}
              </div>
            </div>
            <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 hover:text-rose-600" title="Favorite">
              <Heart className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-4 flex items-end justify-between gap-4">
            <div className="text-xs text-slate-500">Per night</div>
            <div className="text-right">
              <div className="text-lg font-black text-slate-900">
                <Price cents={hotel?.price_per_night_cents || hotel?.price_cents} />
              </div>
              <div className="text-xs text-slate-500">+ taxes & fees</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default HotelCard;
