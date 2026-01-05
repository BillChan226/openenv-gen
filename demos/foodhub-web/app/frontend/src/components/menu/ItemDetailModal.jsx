import React, { useMemo, useState } from 'react';
import { X } from 'lucide-react';

import Modal from '../ui/Modal.jsx';
import Price from '../ui/Price.jsx';
import QuantityStepper from '../ui/QuantityStepper.jsx';
import Button from '../ui/Button.jsx';

export function ItemDetailModal({ open, onClose, product, onAdd }) {
  const [qty, setQty] = useState(1);

  const name = product?.name || product?.title || 'Item';
  const desc = product?.description || '';
  const img = product?.image_url || product?.imageUrl || null;
  const priceCents = useMemo(() => {
    if (!product) return null;
    return (
      product.price_cents ??
      product.priceCents ??
      (typeof product.price === 'number' ? Math.round(product.price * 100) : null)
    );
  }, [product]);

  return (
    <Modal open={open} onClose={onClose}>
      <div className="relative overflow-hidden rounded-3xl bg-white shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-neutral-700 shadow hover:bg-white transition"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        {img ? (
          <div className="h-44 w-full bg-neutral-100">
            <img src={img} alt={name} className="h-full w-full object-cover" />
          </div>
        ) : null}

        <div className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-extrabold tracking-tight text-neutral-900">{name}</h3>
              {desc ? <p className="mt-1 text-sm text-neutral-600">{desc}</p> : null}
            </div>
            {priceCents != null ? (
              <div className="shrink-0 rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200">
                <Price cents={priceCents} />
              </div>
            ) : null}
          </div>

          <div className="mt-5 flex items-center justify-between gap-4">
            <QuantityStepper value={qty} onChange={setQty} min={1} max={20} />
            <Button
              type="button"
              variant="primary"
              onClick={() => {
                if (!product) return;
                onAdd?.(product, qty);
                onClose?.();
                setQty(1);
              }}
              className="min-w-32"
            >
              Add to cart
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default ItemDetailModal;
