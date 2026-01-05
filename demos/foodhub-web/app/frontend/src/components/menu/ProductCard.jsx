import React from 'react';
import { formatCents } from '../../utils/money';

export function ProductCard({ product, onClick }) {
  if (!product) return null;

  const name = product.name;
  const description = product.description;
  const priceCents =
    product.price_cents ?? product.priceCents ?? product.base_price_cents ?? product.basePriceCents;
  const imageUrl = product.image_url || product.imageUrl;

  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left rounded-2xl border border-zinc-200 bg-white shadow-sm hover:shadow transition overflow-hidden"
    >
      <div className="flex gap-3 p-4">
        <div className="min-w-0 flex-1">
          <div className="font-extrabold text-zinc-900 truncate">{name}</div>
          {description ? (
            <div className="mt-1 text-sm text-zinc-600 line-clamp-2">{description}</div>
          ) : null}
          <div className="mt-3 text-sm font-semibold text-zinc-900">
            {typeof priceCents === 'number' ? formatCents(priceCents) : '—'}
          </div>
        </div>

        <div className="h-20 w-20 shrink-0 rounded-xl bg-zinc-100 overflow-hidden">
          {imageUrl ? (
            <img src={imageUrl} alt={name} className="h-20 w-20 object-cover" loading="lazy" />
          ) : null}
        </div>
      </div>
    </button>
  );
}

export default ProductCard;
