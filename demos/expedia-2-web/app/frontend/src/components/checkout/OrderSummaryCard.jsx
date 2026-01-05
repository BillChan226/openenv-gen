import React from 'react';
import { formatMoney } from '../../utils/money';

export default function OrderSummaryCard({ cart }) {
  const pricing = cart?.pricing || cart?.totals || {};
  const subtotal = pricing?.subtotal_cents ?? pricing?.subtotal ?? 0;
  const taxes = pricing?.tax_cents ?? pricing?.taxes_cents ?? pricing?.taxes ?? 0;
  const fees = pricing?.fees_cents ?? pricing?.fees ?? 0;
  const discount = pricing?.discount_cents ?? pricing?.discount ?? 0;
  const total = pricing?.total_cents ?? pricing?.total ?? subtotal + taxes + fees - discount;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">Order summary</h2>
      <div className="mt-4 space-y-2 text-sm">
        <div className="flex items-center justify-between text-slate-700">
          <span>Subtotal</span>
          <span className="font-semibold">{formatMoney(subtotal)}</span>
        </div>
        <div className="flex items-center justify-between text-slate-700">
          <span>Taxes</span>
          <span className="font-semibold">{formatMoney(taxes)}</span>
        </div>
        <div className="flex items-center justify-between text-slate-700">
          <span>Fees</span>
          <span className="font-semibold">{formatMoney(fees)}</span>
        </div>
        {discount ? (
          <div className="flex items-center justify-between text-emerald-700">
            <span>Discount</span>
            <span className="font-semibold">- {formatMoney(discount)}</span>
          </div>
        ) : null}
        <div className="my-3 h-px bg-slate-200" />
        <div className="flex items-center justify-between text-slate-900">
          <span className="font-bold">Total</span>
          <span className="text-lg font-extrabold">{formatMoney(total)}</span>
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-500">Youll see the final amount before confirming your booking.</p>
    </div>
  );
}
