import React from 'react';
import { Star } from 'lucide-react';

export function StarRating({ rating = 0 }) {
  const r = Math.max(0, Math.min(5, Number(rating) || 0));
  const full = Math.floor(r);
  return (
    <div className="inline-flex items-center gap-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={
            'h-4 w-4 ' + (i < full ? 'fill-amber-400 text-amber-400' : 'text-slate-300')
          }
        />
      ))}
      <span className="ml-1 text-xs font-semibold text-slate-600">{r.toFixed(1)}</span>
    </div>
  );
}

export default StarRating;
