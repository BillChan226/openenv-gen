import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

export function Modal({ open, title, onClose, children, className }) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div
          className={clsx(
            'w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-card',
            className
          )}
          role="dialog"
          aria-modal="true"
        >
          <div className="flex items-start justify-between gap-4 border-b border-neutral-100 px-5 py-4">
            <div>
              {title ? <div className="text-lg font-extrabold text-neutral-900">{title}</div> : null}
            </div>
            <button
              onClick={onClose}
              className="rounded-full p-2 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="max-h-[75vh] overflow-auto">{children}</div>
        </div>
      </div>
    </div>
  );
}

export default Modal;
