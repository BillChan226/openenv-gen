import React from 'react';
import { Minus, Plus } from 'lucide-react';
import clsx from 'clsx';

export function QuantityStepper({ value, min = 1, max = 99, onChange, className }) {
  const decDisabled = value <= min;
  const incDisabled = value >= max;

  return (
    <div className={clsx('inline-flex items-center gap-2 rounded-full bg-neutral-100 p-1', className)}>
      <button
        type="button"
        disabled={decDisabled}
        onClick={() => onChange?.(Math.max(min, value - 1))}
        className="grid h-9 w-9 place-items-center rounded-full bg-white text-neutral-900 shadow-sm hover:bg-neutral-50 disabled:opacity-40"
        aria-label="Decrease"
      >
        <Minus className="h-4 w-4" />
      </button>
      <div className="min-w-8 text-center text-sm font-extrabold text-neutral-900">{value}</div>
      <button
        type="button"
        disabled={incDisabled}
        onClick={() => onChange?.(Math.min(max, value + 1))}
        className="grid h-9 w-9 place-items-center rounded-full bg-white text-neutral-900 shadow-sm hover:bg-neutral-50 disabled:opacity-40"
        aria-label="Increase"
      >
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
}

export default QuantityStepper;
