import React, { useEffect, useState } from 'react';
import { User } from 'lucide-react';
import { me, getAddresses, getPaymentMethods } from '../services/api';

export function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        const [u, a, p] = await Promise.all([me(), getAddresses(), getPaymentMethods()]);
        if (!mounted) return;
        setProfile(u?.user || u);
        setAddresses(Array.isArray(a) ? a : a?.items || []);
        setPaymentMethods(Array.isArray(p) ? p : p?.items || []);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#FF3008]/10 text-[#FF3008]">
          <User className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-neutral-900">Profile</h1>
          <p className="text-sm text-neutral-600">Manage your account details.</p>
        </div>
      </div>

      {loading ? (
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="h-40 rounded-2xl border border-neutral-200 bg-white shadow-sm" />
          <div className="h-40 rounded-2xl border border-neutral-200 bg-white shadow-sm" />
          <div className="h-40 rounded-2xl border border-neutral-200 bg-white shadow-sm" />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold text-neutral-500">Signed in as</div>
            <div className="mt-1 text-lg font-extrabold text-neutral-900">{profile?.name || '—'}</div>
            <div className="mt-1 text-sm text-neutral-600">{profile?.email || '—'}</div>
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="text-sm font-bold text-neutral-900">Addresses</div>
            <div className="mt-3 space-y-2">
              {addresses.length ? (
                addresses.map((a) => (
                  <div key={a.id} className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
                    {a.label || a.line1 || a.address1 || `Address ${a.id}`}
                  </div>
                ))
              ) : (
                <div className="text-sm text-neutral-600">No saved addresses.</div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="text-sm font-bold text-neutral-900">Payment methods</div>
            <div className="mt-3 space-y-2">
              {paymentMethods.length ? (
                paymentMethods.map((p) => (
                  <div key={p.id} className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
                    {p.brand ? `${p.brand} •••• ${p.last4}` : p.label || `Method ${p.id}`}
                  </div>
                ))
              ) : (
                <div className="text-sm text-neutral-600">No saved payment methods.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfilePage;
