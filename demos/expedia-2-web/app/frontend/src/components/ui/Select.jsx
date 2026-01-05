import React from 'react';
import clsx from 'clsx';

export function Select({ className, children, ...props }) {
  return (
    <select
      className={clsx(
        'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20',
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export default Select;
