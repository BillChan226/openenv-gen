import React from 'react';
import Goods from './Goods.jsx';

export function Retail() {
  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-br from-indigo-600 to-indigo-500 text-white p-5 sm:p-6 shadow-[0_20px_70px_rgba(79,70,229,0.25)]">
        <div className="text-xs font-semibold uppercase tracking-wider text-white/80">Retail</div>
        <div className="mt-2 text-2xl font-black tracking-tight">Shop retail near you.</div>
        <div className="mt-1 text-sm text-white/90">Convenience, pharmacy, and more.</div>
      </div>
      <Goods />
    </div>
  );
}

export default Retail;
