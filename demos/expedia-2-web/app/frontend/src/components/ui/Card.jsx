import React from 'react';
import clsx from 'clsx';

export function Card({ className, ...props }) {
  return (
    <div
      className={clsx(
        'rounded-card border border-slate-200 bg-white shadow-sm',
        className
      )}
      {...props}
    />
  );
}

export default Card;
