export function formatMoney(cents, currency = 'USD', locale = 'en-US') {
  const amount = Number(cents || 0) / 100;
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0
  }).format(amount);
}

export default formatMoney;
