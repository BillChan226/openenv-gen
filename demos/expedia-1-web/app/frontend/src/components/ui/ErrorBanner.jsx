import React from 'react';
import clsx from 'clsx';
import { AlertTriangle } from 'lucide-react';

export default function ErrorBanner({ title = 'Something went wrong', message, className }) {
  if (!message) return null;
  return (
    <div
      className={clsx(
        'flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-900',
        className
      )}
      role="alert"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 text-red-600" />
      <div>
        <div className="text-sm font-semibold">{title}</div>
        <div className="mt-1 text-sm text-red-800">{String(message)}</div>
      </div>
    </div>
  );
}
