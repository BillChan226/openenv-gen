import { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../components/ui/Toast';
import Button from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import Container from '../components/ui/Container';
import Card from '../components/ui/Card';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});

export default function LoginPage() {
  const { login } = useAuth();
  const cartApi = useCart();
  const toast = useToast();
  const nav = useNavigate();
  const loc = useLocation();
  const [serverError, setServerError] = useState(null);

  const redirectTo = useMemo(() => {
    // RequireAuth sets { from: '/cart?...' }
    const from = loc.state?.from;
    if (typeof from === 'string' && from.startsWith('/')) return from;
    return '/';
  }, [loc.state]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' }
  });

  const onSubmit = async (values) => {
    setServerError(null);
    try {
      await login(values);

      // If a page redirected here while trying to add something to cart,
      // it may pass a pending item in location state.
      const pendingCartItem = loc.state?.pendingCartItem;
      if (pendingCartItem) {
        const addFn = cartApi?.addItem || cartApi?.addToCart || cartApi?.add;
        if (typeof addFn === 'function') {
          await addFn(pendingCartItem);
        }
      }

      toast.success('Welcome back!', 'You are now signed in.');
      nav(redirectTo, { replace: true });
    } catch (e) {
      const msg = e?.response?.data?.error || e?.message || 'Login failed';
      setServerError(msg);
      toast.error('Login failed', msg);
    }
  };

  return (
    <div className="bg-gradient-to-b from-white via-slate-50 to-slate-50">
      <Container className="py-10">
        <div className="mx-auto max-w-md">
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Sign in</h1>
          <p className="mt-2 text-sm text-slate-600">
            New here?{' '}
            <Link className="font-semibold text-brand-600 hover:text-brand-700" to="/register">
              Create an account
            </Link>
          </p>

          <Card className="mt-6 p-6 shadow-lg">
            <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="text-sm font-semibold text-slate-800" htmlFor="email">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="testuser@example.com"
                  className="mt-1"
                  {...register('email')}
                />
                {errors.email && <p className="mt-1 text-xs text-rose-600">{errors.email.message}</p>}
              </div>

              <div>
                <label className="text-sm font-semibold text-slate-800" htmlFor="password">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="Your password"
                  className="mt-1"
                  {...register('password')}
                />
                {errors.password && (
                  <p className="mt-1 text-xs text-rose-600">{errors.password.message}</p>
                )}
              </div>

              {serverError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {serverError}
                </div>
              )}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in…' : 'Sign in'}
              </Button>

              <div className="text-center text-xs text-slate-500">
                By signing in you agree to our terms and privacy policy.
              </div>
            </form>
          </Card>

          <div className="mt-6 text-center">
            <Link className="text-sm font-semibold text-slate-700 hover:text-brand-700" to="/">
              Back to home
            </Link>
          </div>
        </div>
      </Container>
    </div>
  );
}
