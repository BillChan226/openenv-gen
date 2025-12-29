import { useEffect, useState } from 'react';
import { getAccountOverview } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { Spinner } from '../components/ui/Spinner.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { Button } from '../components/ui/Button.jsx';

export default function AccountPage() {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const res = await getAccountOverview();
        if (!cancelled) setOverview(res);
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load account');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="container-page py-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My account</h1>
          <p className="mt-1 text-sm text-slate-600">Manage your profile and preferences.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={logout} data-testid="account-logout">
            Sign out
          </Button>
        </div>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner />
          </div>
        ) : error ? (
          <Alert variant="error">{error}</Alert>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-900">Signed-in user</div>
              <div className="mt-2 text-sm text-slate-700">
                <div>
                  <span className="font-medium">Email:</span> {user?.email || overview?.user?.email || '—'}
                </div>
                <div className="mt-1">
                  <span className="font-medium">Name:</span> {user?.name || overview?.user?.name || '—'}
                </div>
              </div>
            </div>

            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-900">Account overview</div>
              <div className="mt-2 text-sm text-slate-700">
                <div>
                  <span className="font-medium">Wishlist items:</span> {overview?.wishlistCount ?? overview?.wishlist?.length ?? '—'}
                </div>
                <div className="mt-1">
                  <span className="font-medium">Cart items:</span> {overview?.cartCount ?? overview?.cart?.items?.length ?? '—'}
                </div>
              </div>
            </div>

            <div className="rounded-lg border bg-white p-4 shadow-sm lg:col-span-2">
              <div className="text-sm font-semibold text-slate-900">Raw response</div>
              <pre className="mt-2 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-700" data-testid="account-raw">
                {JSON.stringify(overview, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
