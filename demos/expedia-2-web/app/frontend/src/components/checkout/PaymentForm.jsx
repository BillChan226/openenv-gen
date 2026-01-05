import React, { useMemo, useState } from 'react';
import Button from '../ui/Button';
import { Input } from '../ui/Input';

export default function PaymentForm({ paymentMethods = [], onSubmit, loading }) {
  const [mode, setMode] = useState(paymentMethods?.length ? 'saved' : 'new');
  const [selectedId, setSelectedId] = useState(paymentMethods?.[0]?.id || '');

  const [cardNumber, setCardNumber] = useState('4242 4242 4242 4242');
  const [exp, setExp] = useState('12/34');
  const [cvc, setCvc] = useState('123');
  const [name, setName] = useState('');

  const canUseSaved = useMemo(() => paymentMethods?.length > 0, [paymentMethods]);

  const submit = async (e) => {
    e.preventDefault();
    if (mode === 'saved') {
      await onSubmit?.({ type: 'saved', payment_method_id: selectedId });
    } else {
      await onSubmit?.({
        type: 'new',
        card_number: cardNumber,
        exp,
        cvc,
        name
      });
    }
  };

  return (
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold text-slate-900">Payment</h2>
      <p className="mt-1 text-sm text-slate-600">Choose a saved card or use a test card.</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setMode('saved')}
          disabled={!canUseSaved}
          className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
            mode === 'saved'
              ? 'border-blue-600 bg-blue-50 text-blue-700'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          } ${!canUseSaved ? 'cursor-not-allowed opacity-50' : ''}`}
        >
          Saved
        </button>
        <button
          type="button"
          onClick={() => setMode('new')}
          className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
            mode === 'new'
              ? 'border-blue-600 bg-blue-50 text-blue-700'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          New card
        </button>
      </div>

      {mode === 'saved' ? (
        <div className="mt-5">
          <label className="text-sm font-semibold text-slate-800">Select card</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
          >
            {paymentMethods.map((pm) => (
              <option key={pm.id} value={pm.id}>
                {(pm.brand || 'Card') + ' •••• ' + (pm.last4 || pm.last_4)}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Input label="Name on card" value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex Morgan" />
          </div>
          <div className="md:col-span-2">
            <Input
              label="Card number"
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              placeholder="4242 4242 4242 4242"
            />
          </div>
          <Input label="Expiration" value={exp} onChange={(e) => setExp(e.target.value)} placeholder="MM/YY" />
          <Input label="CVC" value={cvc} onChange={(e) => setCvc(e.target.value)} placeholder="123" />

          <div className="md:col-span-2 rounded-xl bg-blue-50 px-4 py-3 text-xs text-blue-900">
            Test card: <span className="font-semibold">4242 4242 4242 4242</span>
          </div>
        </div>
      )}

      <Button type="submit" disabled={loading} className="mt-6 w-full">
        {loading ? 'Processing…' : 'Pay and book'}
      </Button>
    </form>
  );
}
