import React, { useEffect, useMemo, useState } from 'react';
import Button from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useAuth } from '../contexts/AuthContext';
import { deletePaymentMethod, getMe, listPaymentMethods, updateProfile } from '../services/api';

export default function ProfilePage() {
  const { user: authedUser, refresh, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const [me, setMe] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');

  const initials = useMemo(() => {
    const n = (me?.full_name || me?.name || '').trim();
    if (!n) return 'U';
    const parts = n.split(/\s+/).slice(0, 2);
    return parts.map((p) => p[0]?.toUpperCase()).join('');
  }, [me]);

  useEffect(() => {
    let mounted = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const [nextMe, pm] = await Promise.all([getMe(), listPaymentMethods()]);
        if (!mounted) return;
        setMe(nextMe);
        setPaymentMethods(pm || []);
        setFullName(nextMe?.full_name || nextMe?.name || '');
        setEmail(nextMe?.email || '');
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.error?.message || 'Failed to load profile.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    run();
    return () => {
      mounted = false;
    };
  }, [authedUser?.id]);

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await updateProfile({ full_name: fullName, email });
      await refresh();
      const nextMe = await getMe();
      setMe(nextMe);
    } catch (err) {
      setError(err?.response?.data?.error?.message || 'Unable to save changes.');
    } finally {
      setSaving(false);
    }
  };

  const onRemovePaymentMethod = async (id) => {
    setError(null);
    try {
      await deletePaymentMethod(id);
      const pm = await listPaymentMethods();
      setPaymentMethods(pm || []);
    } catch (err) {
      setError(err?.response?.data?.error?.message || 'Unable to remove payment method.');
    }
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <aside className="w-full md:w-80">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-600 text-lg font-bold text-white">
                  {initials}
                </div>
                <div>
                  <div className="text-base font-semibold text-slate-900">{me?.full_name || me?.name || 'Your account'}</div>
                  <div className="text-sm text-slate-600">{me?.email}</div>
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <Button variant="secondary" className="w-full" onClick={logout}>
                  Sign out
                </Button>
              </div>
              <p className="mt-3 text-xs text-slate-500">Manage profile, saved payment methods, and view your trips.</p>
            </div>
          </aside>

          <main className="flex-1">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h1 className="text-xl font-bold text-slate-900">Profile</h1>
              <p className="mt-1 text-sm text-slate-600">Keep your details up to date for faster checkout.</p>

              {error ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                  {error}
                </div>
              ) : null}

              {loading ? (
                <div className="mt-6 animate-pulse space-y-3">
                  <div className="h-10 rounded-xl bg-slate-100" />
                  <div className="h-10 rounded-xl bg-slate-100" />
                  <div className="h-10 rounded-xl bg-slate-100" />
                </div>
              ) : (
                <form onSubmit={onSave} className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                  <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />

                  <div className="md:col-span-2">
                    <Button type="submit" disabled={saving}>
                      {saving ? 'Saving…' : 'Save changes'}
                    </Button>
                  </div>
                </form>
              )}
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Payment methods</h2>
                  <p className="mt-1 text-sm text-slate-600">Saved cards for 1-click checkout.</p>
                </div>
              </div>

              <div className="mt-4 divide-y divide-slate-100">
                {paymentMethods?.length ? (
                  paymentMethods.map((pm) => (
                    <div key={pm.id} className="flex items-center justify-between gap-4 py-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">{pm.brand || 'Card'} •••• {pm.last4 || pm.last_4}</div>
                        <div className="text-xs text-slate-600">Expires {pm.exp_month || pm.expMonth}/{pm.exp_year || pm.expYear}</div>
                      </div>
                      <Button variant="ghost" onClick={() => onRemovePaymentMethod(pm.id)}>
                        Remove
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    No saved payment methods yet. Add one during checkout.
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
