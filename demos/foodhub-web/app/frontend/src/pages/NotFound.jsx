import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button.jsx';

export function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="rounded-3xl bg-white shadow-sm ring-1 ring-zinc-200 p-8 text-center max-w-md">
        <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">404</div>
        <div className="mt-2 text-2xl font-black tracking-tight text-zinc-900">Page not found</div>
        <div className="mt-2 text-sm text-zinc-600">The page you’re looking for doesn’t exist.</div>
        <Button asChild className="mt-5">
          <Link to="/">Go home</Link>
        </Button>
      </div>
    </div>
  );
}

export default NotFound;
