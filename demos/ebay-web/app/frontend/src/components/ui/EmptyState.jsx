import { clsx } from 'clsx';

export function EmptyState({ icon: Icon, title, description, action, className }) {
  return (
    <div className={clsx('flex flex-col items-center justify-center py-12 text-center', className)}>
      {Icon ? <Icon className="mb-4 h-12 w-12 text-gray-400" aria-hidden="true" /> : null}
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {description ? <p className="mt-1 max-w-md text-sm text-gray-600">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
