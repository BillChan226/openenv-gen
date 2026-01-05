import React from 'react';
import { Link } from 'react-router-dom';
import { Heart, Star } from 'lucide-react';
import { formatCents } from '../../utils/money.js';

export function RestaurantCard({ restaurant, onToggleFavorite }) {
  if (!restaurant) return null;

  const {
    id,
    name,
    hero_image_url,
    image_url,
    cuisine,
    cuisine_tags,
    rating,
    rating_count,
    delivery_fee_cents,
    delivery_time_min,
    delivery_time_max,
    price_tier,
    is_favorited,
  } = restaurant;

  const img = hero_image_url || image_url;
  const tags = cuisine_tags || (cuisine ? [cuisine] : []);

  return (
    <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
      <div className="relative">
        <Link to={`/restaurants/${id}`} className="block">
          <div className="h-36 w-full bg-neutral-100">
            {img ? (
              <img
                src={img}
                alt={name}
                className="h-36 w-full object-cover"
                loading="lazy"
              />
            ) : null}
          </div>
        </Link>

        <button
          type="button"
          aria-label={is_favorited ? 'Remove from favorites' : 'Add to favorites'}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleFavorite?.(restaurant);
          }}
          className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-white/90 text-neutral-800 shadow"
        >
          <Heart className={`h-4 w-4 ${is_favorited ? 'fill-[#FF3008] text-[#FF3008]' : ''}`} />
        </button>
      </div>

      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Link
              to={`/restaurants/${id}`}
              className="block truncate text-base font-extrabold text-neutral-900"
            >
              {name}
            </Link>

            {tags.length > 0 ? (
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-neutral-600">
                {tags.slice(0, 3).map((t) => (
                  <span key={t} className="rounded-full bg-neutral-100 px-2 py-1">
                    {t}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="shrink-0 rounded-xl bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-900">
            <span className="inline-flex items-center gap-1">
              <Star className="h-3.5 w-3.5 text-amber-500" />
              {typeof rating === 'number' ? rating.toFixed(1) : '—'}
            </span>
            {rating_count ? (
              <span className="ml-1 text-neutral-600">({rating_count})</span>
            ) : null}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-neutral-700">
          <span>
            {delivery_time_min && delivery_time_max
              ? `${delivery_time_min}-${delivery_time_max} min`
              : delivery_time_min
                ? `${delivery_time_min} min`
                : '—'}
          </span>
          <span className="text-neutral-300">•</span>
          <span>
            Delivery {typeof delivery_fee_cents === 'number' ? formatCents(delivery_fee_cents) : '—'}
          </span>
          {price_tier ? (
            <>
              <span className="text-neutral-300">•</span>
              <span>{price_tier}</span>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default RestaurantCard;
