import React from 'react';

export function formatMoney(cents, currency = 'USD') {
  if (cents === null || cents === undefined) return '';
  const amount = Number(cents) / 100;
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount);
}

export function Price({ cents, currency = 'USD', className = '' }) {
  return <span className={className}>{formatMoney(cents, currency)}</span>;
}

export default Price;
