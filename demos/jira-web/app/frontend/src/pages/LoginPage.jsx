import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../state/AuthContext.jsx';
import { useToast } from '../state/ToastContext.jsx';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Default to QA-friendly seeded credentials.
  const [email, setEmail] = useState('test@example.com');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard');
  }, [isAuthenticated, navigate]);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.push({ title: 'Welcome back', variant: 'success' });
      const to = location.state?.from || '/dashboard';
      navigate(to);
    } catch (err) {
      toast.push({ title: 'Login failed', message: err?.message || 'Invalid credentials', variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-bg">
      <div className="surface w-full max-w-md p-6 shadow-card">
        <h1 className="text-xl font-semibold">Sign in</h1>
        <p className="text-sm text-fg-muted mt-1">Use the demo credentials to explore the app.</p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="input mt-1"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              data-testid="login-email"
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input mt-1"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              data-testid="login-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary w-full"
            disabled={loading}
            data-testid="login-submit"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="text-xs text-fg-muted">
            Demo: <span className="font-mono">test@example.com</span> / <span className="font-mono">password123</span>
            <span className="mx-2">•</span>
            Admin: <span className="font-mono">admin@example.com</span> / <span className="font-mono">Password123!</span>
          </div>
        </form>
      </div>
    </div>
  );
}
