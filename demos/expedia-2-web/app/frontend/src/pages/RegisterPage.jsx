import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const schema = z
  .object({
    full_name: z.string().min(2, 'Enter your name'),
    email: z.string().email('Enter a valid email'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
    confirm_password: z.string().min(6, 'Confirm your password')
  })
  .refine((v) => v.password === v.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match'
  });

export default function RegisterPage() {
  const { register: doRegister } = useAuth();
  const nav = useNavigate();
  const [serverError, setServerError] = useState(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { full_name: '', email: '', password: '', confirm_password: '' }
  });

  const onSubmit = async (values) => {
    setServerError(null);
    try {
      await doRegister({ full_name: values.full_name, email: values.email, password: values.password });
      nav('/');
    } catch (e) {
      const msg = e?.response?.data?.error?.message || 'Unable to create account. Please try again.';
      setServerError(msg);
    }
  };

  return (
    <div className="min-h-[70vh] bg-gradient-to-b from-blue-50 to-white">
      <div className="mx-auto max-w-md px-4 py-10">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Create account</h1>
          <p className="mt-1 text-sm text-slate-600">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-blue-700 hover:text-blue-800">
              Sign in
            </Link>
          </p>

          {serverError ? (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {serverError}
            </div>
          ) : null}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <Input
              label="Full name"
              placeholder="Alex Morgan"
              error={errors.full_name?.message}
              {...register('full_name')}
            />
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register('password')}
            />
            <Input
              label="Confirm password"
              type="password"
              placeholder="••••••••"
              error={errors.confirm_password?.message}
              {...register('confirm_password')}
            />

            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? 'Creating…' : 'Create account'}
            </Button>

            <div className="text-center text-sm text-slate-600">
              Well never share your email.
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
