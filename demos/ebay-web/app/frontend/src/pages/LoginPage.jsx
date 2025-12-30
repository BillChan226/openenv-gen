import { useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { Button } from '../components/ui/Button.jsx';

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = useMemo(() => {
    const params = new URLSearchParams(location.search || '');
    const next = params.get('next');
    if (next) return next;
    const st = location.state;
    return (st && typeof st === 'object' && st.from) || '/account';
  }, [location.search, location.state]);

  const [email, setEmail] = useState('demo@ebay.local');
  const [password, setPassword] = useState('demo');
  const [error, setError] = useState('');

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password) {
      setError('Email and password are required');
      return;
    }
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (e2) {
      setError(e2?.message || 'Login failed');
    }
  }

  return (
    <div className="container-page py-10">
      <div className="mx-auto max-w-md rounded-xl border bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Sign in</h1>
        <p className="mt-1 text-sm text-slate-600">Use the demo credentials to continue.</p>

        {error ? (
          <div className="mt-4">
            <Alert variant="error" onClose={() => setError('')}>
              {error}
            </Alert>
          </div>
        ) : null}

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <div className="text-sm font-medium text-slate-700">Email</div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
              placeholder="you@example.com"
              data-testid="login-email"
            />
          </label>

          <label className="block">
            <div className="text-sm font-medium text-slate-700">Password</div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus-ring"
              placeholder="••••••••"
              data-testid="login-password"
            />
          </label>

          <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit">
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>

          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <div className="font-semibold text-slate-700">Demo credentials</div>
            <div className="mt-1">Email: demo@ebay.local</div>
            <div>Password: demo</div>
          </div>
        </form>
      </div>
    </div>
  );
}
