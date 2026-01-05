import React, { useState } from 'react';
import Button from '../ui/Button';
import { Input } from '../ui/Input';
import { formatMoney } from '../../utils/money';

export default function CartSummaryCard({ pricing, promoCode, onApplyPromo, onCheckout }) {
  const [code, setCode] = useState(promoCode || '');
  const subtotal = pricing?.subtotal_cents ?? pricing?.subtotal ?? 0;
  const taxes = pricing?.tax_cents ?? pricing?.taxes_cents ?? pricing?.taxes ?? 0;
  const fees = pricing?.fees_cents ?? pricing?.fees ?? 0;
  const discount = pricing?.discount_cents ?? pricing?.discount ?? 0;
  const total = pricing?.total_cents ?? pricing?.total ?? 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">Summary</h2>

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
          <span className="text-lg font-extrabold">{formatMoney(total || subtotal + taxes + fees - discount)}</span>
        </div>
      </div>

      <div className="mt-5">
        <div className="flex gap-2">
          <Input label="Promo code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="SAVE10" />
          <div className="pt-7">
            <Button variant="secondary" onClick={() => onApplyPromo?.(code)}>
              Apply
            </Button>
          </div>
        </div>
      </div>

      <Button className="mt-5 w-full" onClick={onCheckout}>
        Go to checkout
      </Button>

      <p className="mt-3 text-xs text-slate-500">Prices include estimated taxes and fees. Final total may vary.</p>
    </div>
  );
}
