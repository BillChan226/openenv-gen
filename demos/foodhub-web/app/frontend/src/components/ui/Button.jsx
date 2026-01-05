import React from 'react';
import clsx from 'clsx';

export function Button({ children, type, variant = 'primary', size = 'md', className, ...props }) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-brand-500 text-white shadow-soft hover:bg-brand-600',
    secondary: 'bg-neutral-900 text-white hover:bg-neutral-800',
    ghost: 'bg-transparent text-neutral-900 hover:bg-neutral-100',
    outline:
      'bg-white text-neutral-900 border border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
  };

  const sizes = {
    sm: 'h-9 px-4 text-sm',
    md: 'h-11 px-5 text-sm',
    lg: 'h-12 px-6 text-base'
  };

  return (
    <button
      type={type || 'button'}
      className={clsx(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
