import { X } from 'lucide-react';
import { useEffect } from 'react';

export function Modal({ open, title, children, onClose, footer, testid }) {
  useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === 'Escape') onClose?.();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/50"
      role="dialog"
      aria-modal="true"
      onMouseDown={(e) => {
        // Only close when the user interacts with the overlay itself (outside the panel)
        if (e.target === e.currentTarget) onClose?.();
      }}
      data-testid={testid ? `${testid}-backdrop` : 'modal-backdrop'}
    >
      <div
        className="relative z-[1] w-full max-w-lg surface shadow-card"
        onMouseDown={(e) => e.stopPropagation()}
        data-testid={testid ? `${testid}-panel` : 'modal-panel'}
      >
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border">
          <div className="text-base font-semibold">{title}</div>
          <button
            type="button"
            className="btn btn-ghost h-9 w-9 p-0"
            onClick={onClose}
            aria-label="Close"
            data-testid="modal-close"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="px-5 py-4 border-t border-border">{footer}</div>}
      </div>
    </div>
  );
}
