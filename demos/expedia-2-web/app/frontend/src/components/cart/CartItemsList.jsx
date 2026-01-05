import React from 'react';
import Button from '../ui/Button';
import { formatMoney } from '../../utils/money';

function CartItemRow({ item, onRemove }) {
  const title = item?.title || item?.name || item?.product_name || `${item?.item_type || 'Item'}`;
  const subtitle = item?.subtitle || item?.description;
  const priceCents = item?.price_total_cents ?? item?.total_price_cents ?? item?.price_cents ?? 0;

  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        {subtitle ? <div className="mt-0.5 text-xs text-slate-600">{subtitle}</div> : null}
        <div className="mt-2 text-xs text-slate-500">Type: {item?.item_type || item?.type || '—'}</div>
      </div>

      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <div className="text-right">
          <div className="text-xs text-slate-500">Total</div>
          <div className="text-base font-bold text-slate-900">{formatMoney(priceCents)}</div>
        </div>
        <Button variant="ghost" onClick={() => onRemove?.(item?.id)}>
          Remove
        </Button>
      </div>
    </div>
  );
}

export default function CartItemsList({ cart, onUpdateItem, onRemoveItem }) {
  const items = cart?.items || cart?.cart_items || [];

  return (
    <div className="space-y-3">
      {items?.length ? (
        items.map((it) => (
          <CartItemRow
            key={it.id}
            item={it}
            onUpdate={(payload) => onUpdateItem?.(it.id, payload)}
            onRemove={onRemoveItem}
          />
        ))
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm">
          Your cart is empty.
        </div>
      )}
    </div>
  );
}
