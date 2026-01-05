import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

import Button from '../components/ui/Button.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="rounded-3xl bg-white shadow-sm ring-1 ring-zinc-200 p-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[#FF3008] text-white flex items-center justify-center font-black">
              D
            </div>
            <div>
              <div className="text-lg font-extrabold tracking-tight text-zinc-900">Sign in</div>
              <div className="text-sm text-zinc-600">Use your account to place orders</div>
            </div>
          </div>

          <form
            className="mt-5 space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                setLoading(true);
                await login({ email, password });
                toast.success('Welcome back');
                navigate('/');
              } catch (err) {
                toast.error(err?.message || 'Login failed');
              } finally {
                setLoading(false);
              }
            }}
          >
            <div>
              <label className="text-xs font-semibold text-zinc-700">Email</label>
              <input
                className="mt-1 w-full rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-[#FF3008]/15 focus:border-[#FF3008] transition"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                type="email"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700">Password</label>
              <input
                className="mt-1 w-full rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-[#FF3008]/15 focus:border-[#FF3008] transition"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                type="password"
                autoComplete="current-password"
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>

            <div className="text-xs text-zinc-500">
              Demo app: if you don’t have credentials, use a seeded user from the backend.
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;
