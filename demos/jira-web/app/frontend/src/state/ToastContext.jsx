import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { X } from 'lucide-react';

const ToastContext = createContext(null);

let idSeq = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback((toast) => {
    const id = idSeq++;
    const next = {
      id,
      title: toast.title,
      message: toast.message,
      variant: toast.variant || 'info',
      timeoutMs: toast.timeoutMs ?? 3000,
    };
    setToasts((t) => [next, ...t]);
    if (next.timeoutMs) setTimeout(() => remove(id), next.timeoutMs);
    return id;
  }, [remove]);

  const value = useMemo(() => ({ push, remove }), [push, remove]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="fixed right-4 top-4 z-[100] flex w-[min(420px,calc(100vw-2rem))] flex-col gap-2"
        aria-live="polite"
        aria-atomic="true"
        data-testid="toast"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={
              'surface shadow-card px-4 py-3 flex gap-3 items-start ' +
              (t.variant === 'success'
                ? 'border-success/30'
                : t.variant === 'error'
                  ? 'border-danger/30'
                  : 'border-border')
            }
            role="status"
          >
            <div className="flex-1">
              {t.title && <div className="text-sm font-semibold">{t.title}</div>}
              {t.message && <div className="text-sm text-fg-muted mt-0.5">{t.message}</div>}
            </div>
            <button
              type="button"
              className="btn btn-ghost h-8 w-8 p-0"
              aria-label="Dismiss"
              data-testid="toast-dismiss"
              onClick={() => remove(t.id)}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
