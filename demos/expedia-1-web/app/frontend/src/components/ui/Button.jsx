import React from 'react';
import clsx from 'clsx';

export default function Button({
  variant = 'primary',
  size = 'md',
  className,
  asChild = false,
  ...props
}) {
  const Comp = asChild ? 'span' : 'button';
  return (
    <Comp
      className={clsx(
        'btn',
        variant === 'primary' && 'btn-primary',
        variant === 'secondary' && 'btn-secondary',
        variant === 'accent' && 'btn-accent',
        size === 'sm' && 'px-3 py-1.5 text-sm rounded-lg',
        size === 'md' && 'px-4 py-2',
        size === 'lg' && 'px-5 py-2.5 text-base',
        className
      )}
      {...props}
    />
  );
}
