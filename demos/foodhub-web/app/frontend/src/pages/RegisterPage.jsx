import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import Button from '../components/ui/Button';
import { useAuth } from '../contexts/AuthContext';

export function RegisterPage() {
  const { register: doRegister } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const redirectTo = loc.state?.from?.pathname || '/';

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await doRegister({ fullName: name, email, password });
      toast.success('Account created');
      nav(redirectTo, { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.error?.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="mx-auto max-w-md px-4 py-14">
        <div className="rounded-3xl border border-neutral-200 bg-white p-8 shadow-sm">
          <div className="text-center">
            <div className="text-3xl font-extrabold tracking-tight text-neutral-900">Create account</div>
            <div className="mt-2 text-sm text-neutral-600">Sign up to place orders and save favorites.</div>
          </div>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <label className="block">
              <div className="text-xs font-semibold text-neutral-700">Name</div>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                placeholder="Jane Doe"
                required
              />
            </label>

            <label className="block">
              <div className="text-xs font-semibold text-neutral-700">Email</div>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                placeholder="jane@example.com"
                required
              />
            </label>

            <label className="block">
              <div className="text-xs font-semibold text-neutral-700">Password</div>
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#FF3008]/30"
                placeholder="••••••••"
                required
              />
            </label>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creating…' : 'Create account'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-neutral-600">
            Already have an account?{' '}
            <Link className="font-semibold text-[#FF3008] hover:underline" to="/login">
              Log in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
