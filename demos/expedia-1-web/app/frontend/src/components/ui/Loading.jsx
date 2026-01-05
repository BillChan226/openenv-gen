import React from 'react';
import clsx from 'clsx';

export default function Loading({ label = 'Loading…', className }) {
  return (
    <div className={clsx('flex items-center gap-3 text-sm text-slate-600', className)}>
      <span className="relative inline-flex h-5 w-5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-600/30" />
        <span className="relative inline-flex h-5 w-5 rounded-full bg-brand-600" />
      </span>
      <span>{label}</span>
    </div>
  );
}
