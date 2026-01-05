import React from 'react';
import clsx from 'clsx';

export function Spinner({ className }) {
  return (
    <div
      className={clsx(
        'h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-brand-500',
        className
      )}
      aria-label="Loading"
    />
  );
}

export default Spinner;
