import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CartItemsList from '../components/cart/CartItemsList';
import CartSummaryCard from '../components/cart/CartSummaryCard';
import Button from '../components/ui/Button';
import { useCart } from '../contexts/CartContext';

export default function CartPage() {
  const nav = useNavigate();
  const { cart, loading, error, refreshCart, removeItem, applyPromo, clear } = useCart();
  const [promoError, setPromoError] = useState(null);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const pricing = useMemo(() => cart?.pricing || cart?.totals || {}, [cart]);

  const onApplyPromo = async (code) => {
    setPromoError(null);
    try {
      await applyPromo(code);
    } catch (e) {
      setPromoError(e?.response?.data?.error?.message || 'Invalid promo code.');
    }
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900">Cart</h1>
            <p className="mt-1 text-sm text-slate-600">Review your selections before checkout.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={clear}>
              Clear cart
            </Button>
            <Button variant="secondary" onClick={() => nav('/')}
            >
              Continue shopping
            </Button>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error?.response?.data?.error?.message || 'Failed to load cart.'}
          </div>
        ) : null}

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
          <div>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, idx) => (
                  <div key={idx} className="h-24 animate-pulse rounded-2xl bg-white shadow-sm" />
                ))}
              </div>
            ) : (
              <CartItemsList cart={cart} onRemoveItem={removeItem} />
            )}

            {promoError ? (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {promoError}
              </div>
            ) : null}
          </div>

          <CartSummaryCard
            pricing={pricing}
            promoCode={cart?.promo_code || ''}
            onApplyPromo={onApplyPromo}
            onCheckout={() => nav('/checkout')}
          />
        </div>
      </div>
    </div>
  );
}
