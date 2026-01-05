import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BadgePercent, Truck } from 'lucide-react';

export function PromoBanners() {
  return (
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-800 text-white p-5 shadow-[0_18px_60px_rgba(0,0,0,0.25)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">
              <Truck className="h-4 w-4" />
              Free delivery
            </div>
            <h3 className="mt-3 text-lg font-black tracking-tight">$0 delivery fees for your first week</h3>
            <p className="mt-1 text-sm text-white/80 max-w-md">
              Try DashPass-style perks on us. Valid at participating stores.
            </p>
            <Link
              to="/goods"
              className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-white hover:text-white/90"
            >
              Explore deals <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="hidden sm:flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/15">
            <Truck className="h-6 w-6" />
          </div>
        </div>
        <div className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
      </div>

      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#FF3008] to-[#FF3008]/85 text-white p-5 shadow-[0_18px_60px_rgba(255,48,8,0.22)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
              <BadgePercent className="h-4 w-4" />
              Up to 30% off
            </div>
            <h3 className="mt-3 text-lg font-black tracking-tight">Save on groceries & essentials</h3>
            <p className="mt-1 text-sm text-white/90 max-w-md">
              Weekly promos on snacks, drinks, and everyday needs.
            </p>
            <Link
              to="/grocery"
              className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-white hover:text-white/90"
            >
              Start shopping <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="hidden sm:flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/20">
            <BadgePercent className="h-6 w-6" />
          </div>
        </div>
        <div className="pointer-events-none absolute -right-10 -bottom-10 h-44 w-44 rounded-full bg-white/15 blur-2xl" />
      </div>
    </section>
  );
}

export default PromoBanners;
