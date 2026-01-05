import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import Button from '../components/ui/Button';
import Price from '../components/ui/Price';
import { useCart } from '../contexts/CartContext';
import { createOrder, getAddresses, getPaymentMethods } from '../services/api';

function cents(n) {
  return Number.isFinite(n) ? n : 0;
}

function computeServiceFeeCents(subtotalCents) {
  // Backend note: integer rounding (subtotal*5+50)/100
  return Math.floor((subtotalCents * 5 + 50) / 100);
}

export function CheckoutPage() {
  const { cart, refreshCart, clear } = useCart();
  const [placing, setPlacing] = useState(false);
  const [addresses, setAddresses] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [addressId, setAddressId] = useState('');
  const [paymentMethodId, setPaymentMethodId] = useState('');
  const [mode, setMode] = useState('delivery');
  const [promo, setPromo] = useState('');

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [a, p] = await Promise.all([getAddresses(), getPaymentMethods()]);
        if (!mounted) return;
        setAddresses(Array.isArray(a) ? a : a?.items || []);
        setPaymentMethods(Array.isArray(p) ? p : p?.items || []);
        setAddressId((a?.[0]?.id || a?.items?.[0]?.id || '') + '');
        setPaymentMethodId((p?.[0]?.id || p?.items?.[0]?.id || '') + '');
      } catch {
        // ignore
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const pricing = cart?.pricing || {};
  const subtotalCents = cents(pricing.subtotalCents ?? pricing.subtotal_cents);
  const deliveryFeeCents = cents(pricing.deliveryFeeCents ?? pricing.delivery_fee_cents);
  const serviceFeeCents = cents(pricing.serviceFeeCents ?? pricing.service_fee_cents) || computeServiceFeeCents(subtotalCents);
  const taxCents = cents(pricing.taxCents ?? pricing.tax_cents);
  const discountCents = cents(pricing.discountCents ?? pricing.discount_cents);

  const totalCents = useMemo(() => {
    const t = subtotalCents + deliveryFeeCents + serviceFeeCents + taxCents - discountCents;
    return t < 0 ? 0 : t;
  }, [subtotalCents, deliveryFeeCents, serviceFeeCents, taxCents, discountCents]);

  const items = cart?.items || [];

  const placeOrder = async () => {
    setPlacing(true);
    try {
      const payload = {
        addressId: addressId || null,
        paymentMethodId: paymentMethodId || null,
        fulfillment: mode,
        promoCode: promo || null
      };
      await createOrder(payload);
      toast.success('Order placed!');
      await clear();
    } catch (err) {
      const message = err?.response?.data?.error?.message || 'Failed to place order';
      toast.error(message);
    } finally {
      setPlacing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-extrabold tracking-tight text-neutral-900">Checkout</h1>

      {!items.length ? (
        <div className="mt-6 rounded-2xl border border-neutral-200 bg-white p-6 text-sm text-neutral-600 shadow-sm">
          Your cart is empty.
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-neutral-900">Delivery or pickup</h2>
                <div className="flex rounded-xl border border-neutral-200 bg-neutral-50 p-1">
                  {[
                    { key: 'delivery', label: 'Delivery' },
                    { key: 'pickup', label: 'Pickup' }
                  ].map((opt) => (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => setMode(opt.key)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                        mode === opt.key ? 'bg-white shadow text-neutral-900' : 'text-neutral-600 hover:text-neutral-900'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block">
                  <div className="text-xs font-semibold text-neutral-700">Address</div>
                  <select
                    value={addressId}
                    onChange={(e) => setAddressId(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                  >
                    <option value="">Select address</option>
                    {addresses.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.label || a.line1 || a.address1 || `Address ${a.id}`}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <div className="text-xs font-semibold text-neutral-700">Payment</div>
                  <select
                    value={paymentMethodId}
                    onChange={(e) => setPaymentMethodId(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                  >
                    <option value="">Select payment method</option>
                    {paymentMethods.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.brand ? `${p.brand} •••• ${p.last4}` : p.label || `Method ${p.id}`}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-neutral-900">Promo code</h2>
              <div className="mt-3 flex gap-2">
                <input
                  value={promo}
                  onChange={(e) => setPromo(e.target.value)}
                  placeholder="Enter code"
                  className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                />
                <Button type="button" variant="outline" onClick={() => toast('Promo will be applied on place order.')}
                >
                  Apply
                </Button>
              </div>
              <p className="mt-2 text-xs text-neutral-500">Promo validation happens when placing the order.</p>
            </div>

            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-neutral-900">Items</h2>
              <div className="mt-3 space-y-3">
                {items.map((it) => (
                  <div key={it.id} className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-semibold text-neutral-900">{it.name}</div>
                      <div className="text-xs text-neutral-500">Qty {it.quantity}</div>
                    </div>
                    <Price cents={cents(it.totalCents ?? it.total_cents)} className="text-sm font-semibold" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm h-fit">
            <h2 className="text-sm font-bold text-neutral-900">Order summary</h2>
            <div className="mt-4 space-y-2 text-sm">
              <div className="flex items-center justify-between text-neutral-700">
                <span>Subtotal</span>
                <Price cents={subtotalCents} />
              </div>
              <div className="flex items-center justify-between text-neutral-700">
                <span>Delivery fee</span>
                <Price cents={deliveryFeeCents} />
              </div>
              <div className="flex items-center justify-between text-neutral-700">
                <span>Service fee</span>
                <Price cents={serviceFeeCents} />
              </div>
              {taxCents ? (
                <div className="flex items-center justify-between text-neutral-700">
                  <span>Tax</span>
                  <Price cents={taxCents} />
                </div>
              ) : null}
              {discountCents ? (
                <div className="flex items-center justify-between text-neutral-700">
                  <span>Discount</span>
                  <Price cents={-discountCents} />
                </div>
              ) : null}
              <div className="my-3 h-px bg-neutral-200" />
              <div className="flex items-center justify-between text-neutral-900 font-extrabold">
                <span>Total</span>
                <Price cents={totalCents} />
              </div>
            </div>
            <Button className="mt-5 w-full" onClick={placeOrder} disabled={placing}>
              {placing ? 'Placing…' : 'Place order'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default CheckoutPage;
