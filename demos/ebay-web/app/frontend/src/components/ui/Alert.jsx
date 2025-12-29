import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import { clsx } from 'clsx';

const variants = {
  error: { icon: AlertCircle, className: 'bg-red-50 text-red-900 border-red-200' },
  success: { icon: CheckCircle2, className: 'bg-green-50 text-green-900 border-green-200' },
  info: { icon: Info, className: 'bg-blue-50 text-blue-900 border-blue-200' },
};

export function Alert({ variant = 'info', children, onClose }) {
  const { icon: Icon, className } = variants[variant] || variants.info;

  return (
    <div className={clsx('flex items-start gap-3 rounded-lg border p-4', className)} role="alert">
      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1 text-sm leading-5">{children}</div>
      {onClose ? (
        <button
          type="button"
          className="rounded p-1 hover:opacity-70 focus-ring"
          onClick={onClose}
          aria-label="Dismiss"
          data-testid="alert-dismiss"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}
