import React from 'react';
import Goods from './Goods.jsx';

export function Grocery() {
  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-br from-emerald-600 to-emerald-500 text-white p-5 sm:p-6 shadow-[0_20px_70px_rgba(16,185,129,0.25)]">
        <div className="text-xs font-semibold uppercase tracking-wider text-white/80">Grocery</div>
        <div className="mt-2 text-2xl font-black tracking-tight">Fresh groceries, fast.</div>
        <div className="mt-1 text-sm text-white/90">Browse grocery stores and everyday essentials.</div>
      </div>
      <Goods />
    </div>
  );
}

export default Grocery;
