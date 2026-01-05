import React from 'react';
import clsx from 'clsx';

export default function Input({ className, leftIcon: LeftIcon, ...props }) {
  return (
    <div className={clsx('relative', className)}>
      {LeftIcon ? (
        <LeftIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      ) : null}
      <input
        className={clsx('input', LeftIcon && 'pl-9')}
        {...props}
      />
    </div>
  );
}
