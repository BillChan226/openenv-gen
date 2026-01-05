import React from 'react';
import clsx from 'clsx';

export function formatPrice(cents) {
  const n = Number(cents || 0);
  return (n / 100).toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

export function Price({ cents, superscriptCents = true, className }) {
  const n = Number(cents || 0);
  const dollars = Math.floor(Math.abs(n) / 100);
  const centsPart = Math.abs(n) % 100;
  const sign = n < 0 ? '-' : '';

  return (
    <span className={clsx('font-extrabold text-neutral-900', className)}>
      {sign}${dollars.toLocaleString()}
      {superscriptCents ? (
        <sup className="ml-0.5 text-[0.7em] font-bold text-neutral-700">{String(centsPart).padStart(2, '0')}</sup>
      ) : (
        <span className="text-neutral-700">.{String(centsPart).padStart(2, '0')}</span>
      )}
    </span>
  );
}

export default Price;
