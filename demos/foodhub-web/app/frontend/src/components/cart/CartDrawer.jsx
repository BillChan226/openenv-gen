import React, { useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import { ShoppingBag, X } from 'lucide-react';

import Modal from '../ui/Modal.jsx';
import Button from '../ui/Button.jsx';
import CartLineItem from './CartLineItem.jsx';
import CartSummary from './CartSummary.jsx';

import { useNavigate } from 'react-router-dom';
import { useCart } from '../../contexts/CartContext.jsx';

export function CartDrawer({ open, onClose }) {
  const navigate = useNavigate();
  const { cart, loading, updateItemQuantity, removeItem, clearCart } = useCart();
  const [busyId, setBusyId] = useState(null);

  const items = cart?.items || [];

  const title = useMemo(() => {
    const store = cart?.restaurant_name || cart?.store_name;
    return store ? `Cart · ${store}` : 'Cart';
  }, [cart]);

  return (
    <Modal open={open} onClose={onClose} className="max-w-3xl">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-10 w-10 rounded-xl bg-[#FF3008] text-white flex items-center justify-center shadow-sm">
            <ShoppingBag className="h-5 w-5" />
          </div>
          <div>
            <div className="text-base font-extrabold text-zinc-900">{title}</div>
            <div className="text-xs text-zinc-500">Review items, fees, and checkout</div>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-2 hover:bg-zinc-100 transition"
          aria-label="Close cart"
        >
          <X className="h-5 w-5 text-zinc-700" />
        </button>
      </div>

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
        <div className="space-y-3">
          {loading ? (
            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4 text-sm text-zinc-600">
              Loading cart…
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-6 text-center">
              <div className="text-sm font-extrabold text-zinc-900">Your cart is empty</div>
              <div className="mt-1 text-sm text-zinc-600">Add items from a store to get started.</div>
              <Button onClick={onClose} className="mt-4">
                Browse stores
              </Button>
            </div>
          ) : (
            items.map((it) => (
              <CartLineItem
                key={it.id}
                item={it}
                updating={busyId === it.id}
                onUpdateQty={async (nextQty) => {
                  try {
                    setBusyId(it.id);
                    await updateItemQuantity(it.id, nextQty);
                  } finally {
                    setBusyId(null);
                  }
                }}
                onRemove={async () => {
                  try {
                    setBusyId(it.id);
                    await removeItem(it.id);
                  } finally {
                    setBusyId(null);
                  }
                }}
              />
            ))
          )}

          {items.length > 0 ? (
            <div className="flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                onClick={async () => {
                  await clearCart();
                  toast.success('Cart cleared');
                }}
              >
                Clear cart
              </Button>
              <div className="text-xs text-zinc-500">Single-store cart enforced</div>
            </div>
          ) : null}
        </div>

        <div>
          <CartSummary
            cart={cart}
            disabled={items.length === 0 || loading}
            onCheckout={async () => {
              try {
                onClose?.();
                navigate('/checkout');
              } catch (e) {
                toast.error(e?.message || 'Checkout failed');
              }
            }}
          />
        </div>
      </div>
    </Modal>
  );
}

export default CartDrawer;
