import React, { useMemo } from 'react';

import Button from '../ui/Button.jsx';
import Price from '../ui/Price.jsx';

export function CartSummary({ cart, onCheckout, disabled }) {
  const totals = useMemo(() => {
    const subtotal = cart?.subtotal_cents ?? cart?.subtotal ?? 0;
    const delivery = cart?.delivery_fee_cents ?? 0;
    const service = cart?.service_fee_cents ?? 0;
    const tax = cart?.tax_cents ?? 0;
    const total = cart?.total_cents ?? subtotal + delivery + service + tax;
    return { subtotal, delivery, service, tax, total };
  }, [cart]);

  return (
    <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
      <div className="text-sm font-extrabold text-zinc-900">Summary</div>

      <div className="mt-3 space-y-2 text-sm">
        <div className="flex items-center justify-between text-zinc-700">
          <span>Subtotal</span>
          <span className="font-semibold">
            <Price cents={totals.subtotal} />
          </span>
        </div>
        <div className="flex items-center justify-between text-zinc-700">
          <span>Delivery fee</span>
          <span className="font-semibold">
            <Price cents={totals.delivery} />
          </span>
        </div>
        <div className="flex items-center justify-between text-zinc-700">
          <span>Service fee</span>
          <span className="font-semibold">
            <Price cents={totals.service} />
          </span>
        </div>
        <div className="flex items-center justify-between text-zinc-700">
          <span>Estimated tax</span>
          <span className="font-semibold">
            <Price cents={totals.tax} />
          </span>
        </div>

        <div className="pt-3 mt-3 border-t border-zinc-100 flex items-center justify-between">
          <span className="text-zinc-900 font-extrabold">Total</span>
          <span className="text-zinc-900 font-extrabold">
            <Price cents={totals.total} />
          </span>
        </div>
      </div>

      <Button onClick={onCheckout} disabled={disabled} className="mt-4 w-full">
        Checkout
      </Button>

      <div className="mt-3 text-xs text-zinc-500">
        Service fee is calculated at checkout. Some fees and taxes may vary.
      </div>
    </div>
  );
}

export default CartSummary;
