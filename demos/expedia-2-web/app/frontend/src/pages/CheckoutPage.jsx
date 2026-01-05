import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import OrderSummaryCard from '../components/checkout/OrderSummaryCard';
import PaymentForm from '../components/checkout/PaymentForm';
import { checkout, getCart, listPaymentMethods } from '../services/api';

export default function CheckoutPage() {
  const nav = useNavigate();
  const [cart, setCart] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [travelerName, setTravelerName] = useState('');
  const [travelerEmail, setTravelerEmail] = useState('');

  useEffect(() => {
    let mounted = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const [c, pm] = await Promise.all([getCart(), listPaymentMethods()]);
        if (!mounted) return;
        setCart(c);
        setPaymentMethods(pm || []);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.error?.message || 'Failed to load checkout.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    run();
    return () => {
      mounted = false;
    };
  }, []);

  const onPay = async (payment) => {
    setSubmitting(true);
    setError(null);
    try {
      await checkout({
        traveler: { name: travelerName, email: travelerEmail },
        payment
      });
      nav('/trips');
    } catch (e) {
      setError(e?.response?.data?.error?.message || 'Payment failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900">Checkout</h1>
            <p className="mt-1 text-sm text-slate-600">Enter traveler details and confirm payment.</p>
          </div>
          <Button variant="secondary" onClick={() => nav('/cart')}>
            Back to cart
          </Button>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
            <div className="h-72 animate-pulse rounded-2xl bg-white shadow-sm" />
            <div className="h-60 animate-pulse rounded-2xl bg-white shadow-sm" />
          </div>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-bold text-slate-900">Traveler info</h2>
                <p className="mt-1 text-sm text-slate-600">Well send booking confirmation to this email.</p>
                <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Input label="Full name" value={travelerName} onChange={(e) => setTravelerName(e.target.value)} />
                  <Input
                    label="Email"
                    type="email"
                    value={travelerEmail}
                    onChange={(e) => setTravelerEmail(e.target.value)}
                  />
                </div>
              </div>

              <PaymentForm paymentMethods={paymentMethods} onSubmit={onPay} loading={submitting} />
            </div>

            <OrderSummaryCard cart={cart} />
          </div>
        )}
      </div>
    </div>
  );
}
