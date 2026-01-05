export function formatCents(cents, currency = 'USD') {
  const value = typeof cents === 'number' ? cents : Number(cents);
  if (!Number.isFinite(value)) return '';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value / 100);
}

export default formatCents;
