import React from 'react';
import { Link } from 'react-router-dom';

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50">
      <div className="absolute inset-x-0 top-0 h-[420px] bg-gradient-to-r from-brand-800 via-brand-700 to-brand-800" />
      <div className="absolute left-1/2 top-14 h-80 w-[680px] -translate-x-1/2 rounded-full bg-gradient-to-br from-yellow-300/35 via-amber-200/10 to-transparent blur-3xl" />

      <div className="relative">
        <div className="container-app py-10">
          <Link to="/" className="inline-flex items-center gap-2 text-white/90 hover:text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15">
              <span className="text-lg font-extrabold tracking-tight">e</span>
            </span>
            <div className="leading-tight">
              <div className="text-base font-extrabold tracking-tight">Expedia</div>
              <div className="text-xs text-white/75">Voyager</div>
            </div>
          </Link>

          <div className="mx-auto mt-10 max-w-md">
            <div className="rounded-3xl bg-white p-7 shadow-card ring-1 ring-slate-200">
              <div className="text-xl font-extrabold tracking-tight text-slate-900">{title}</div>
              {subtitle ? <div className="mt-2 text-sm text-slate-600">{subtitle}</div> : null}
              <div className="mt-6">{children}</div>
            </div>
            <div className="mt-6 text-center text-xs text-slate-500">
              By continuing, you agree to our Terms and acknowledge our Privacy Policy.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
