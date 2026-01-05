import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';

export default function NotFound() {
  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-16">
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <div className="text-5xl font-black tracking-tight text-slate-900">404</div>
          <div className="mt-3 text-xl font-bold text-slate-900">Page not found</div>
          <p className="mt-2 text-sm text-slate-600">
            The page youre looking for doesnt exist or may have moved.
          </p>
          <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
            <Link to="/">
              <Button>Go home</Button>
            </Link>
            <Link to="/hotels">
              <Button variant="secondary">Browse stays</Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
