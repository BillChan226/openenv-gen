import React from 'react';
import clsx from 'clsx';

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  asChild = false,
  children,
  ...props
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/40 disabled:opacity-60 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-brand-500 text-white hover:bg-brand-600 shadow-sm',
    secondary: 'bg-slate-100 text-slate-900 hover:bg-slate-200',
    outline: 'border border-slate-200 bg-white text-slate-900 hover:bg-slate-50',
    danger: 'bg-rose-600 text-white hover:bg-rose-700'
  };

  const sizes = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-5 py-3 text-base'
  };

  const computedClassName = clsx(base, variants[variant], sizes[size], className);

  // `asChild` allows rendering e.g. <Link> as the underlying element.
  // This avoids invalid DOM nesting (<button><a/></button>) and removes the
  // React warning about unknown props.
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...props,
      className: clsx(computedClassName, children.props.className)
    });
  }

  return (
    <button className={computedClassName} {...props}>
      {children}
    </button>
  );
}

export default Button;
