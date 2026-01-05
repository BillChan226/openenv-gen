import React from 'react';
import { Trash2 } from 'lucide-react';

import Price from '../ui/Price.jsx';
import QuantityStepper from '../ui/QuantityStepper.jsx';
import Button from '../ui/Button.jsx';

export function CartLineItem({ item, updating, onUpdateQty, onRemove }) {
  const name = item?.product_name || item?.name || 'Item';
  const priceCents = item?.unit_price_cents ?? item?.price_cents ?? 0;
  const qty = item?.quantity ?? 1;

  return (
    <div className="flex gap-3 rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-3">
      <div className="h-14 w-14 rounded-xl bg-zinc-100 ring-1 ring-zinc-200 flex items-center justify-center text-zinc-400 text-xs font-semibold">
        IMG
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="truncate text-sm font-bold text-zinc-900">{name}</div>
            <div className="mt-0.5 text-xs text-zinc-500">
              <Price cents={priceCents} /> each
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            disabled={updating}
            onClick={onRemove}
            className="text-zinc-500 hover:text-red-600"
            leftIcon={<Trash2 className="h-4 w-4" />}
          >
            Remove
          </Button>
        </div>

        <div className="mt-2 flex items-center justify-between gap-3">
          <QuantityStepper value={qty} min={1} max={99} onChange={onUpdateQty} disabled={updating} />
          <div className="text-sm font-extrabold text-zinc-900">
            <Price cents={priceCents * qty} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default CartLineItem;
