import React from 'react';
import clsx from 'clsx';

export function Badge({ variant = 'default', className, ...props }) {
  const variants = {
    default: 'bg-slate-100 text-slate-800',
    blue: 'bg-brand-50 text-brand-700 border border-brand-100',
    gold: 'bg-amber-50 text-amber-800 border border-amber-100',
    success: 'bg-emerald-50 text-emerald-800 border border-emerald-100'
  };
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export default Badge;
