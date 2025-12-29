import { clsx } from 'clsx';

export function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-2',
    lg: 'h-12 w-12 border-4',
  };

  return (
    <div
      className={clsx(
        'animate-spin rounded-full border-current border-t-transparent text-gray-600',
        sizes[size] || sizes.md,
        className
      )}
      aria-label="Loading"
      role="status"
    />
  );
}
