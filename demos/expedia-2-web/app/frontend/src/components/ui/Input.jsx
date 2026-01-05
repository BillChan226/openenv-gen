import React, { forwardRef } from 'react';
import clsx from 'clsx';

export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={clsx(
        'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20',
        className
      )}
      {...props}
    />
  );
});

export default Input;
