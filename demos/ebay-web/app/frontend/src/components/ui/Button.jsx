import { clsx } from 'clsx';

export function Button({
  as: Comp = 'button',
  variant = 'primary',
  size = 'md',
  disabled,
  loading,
  className,
  children,
  ...props
}) {
  const variants = {
    primary: 'bg-brand-blue text-white hover:opacity-95',
    secondary: 'bg-white text-gray-900 border border-gray-300 hover:bg-gray-50',
    ghost: 'bg-transparent text-brand-blue hover:bg-blue-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  const sizes = {
    sm: 'h-8 px-3 text-sm',
    md: 'h-9 px-4 text-sm',
    lg: 'h-10 px-5 text-base',
  };

  return (
    <Comp
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded font-semibold transition focus-ring disabled:cursor-not-allowed disabled:opacity-60',
        variants[variant] || variants.primary,
        sizes[size] || sizes.md,
        className
      )}
      disabled={disabled || loading}
      data-testid={props['data-testid']}
      {...props}
    >
      {loading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" /> : null}
      {children}
    </Comp>
  );
}
