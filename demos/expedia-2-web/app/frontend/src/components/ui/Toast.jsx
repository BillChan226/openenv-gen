import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import clsx from 'clsx';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((toast) => {
    const id = crypto?.randomUUID?.() || String(Date.now() + Math.random());
    const t = { id, type: 'info', title: '', message: '', ...toast };
    setToasts((prev) => [...prev, t]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, toast?.durationMs || 3500);
  }, []);

  const api = useMemo(
    () => ({
      push,
      success: (message, opts = {}) =>
        push({ type: 'success', title: opts.title || 'Success', message, ...opts }),
      error: (message, opts = {}) =>
        push({ type: 'error', title: opts.title || 'Something went wrong', message, ...opts }),
      info: (message, opts = {}) => push({ type: 'info', title: opts.title || '', message, ...opts })
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed right-4 top-4 z-50 flex w-[92vw] max-w-sm flex-col gap-3">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              'rounded-xl border bg-white p-4 shadow-lg',
              t.type === 'success' && 'border-emerald-200',
              t.type === 'error' && 'border-rose-200',
              t.type === 'info' && 'border-slate-200'
            )}
          >
            {t.title ? <div className="text-sm font-bold text-slate-900">{t.title}</div> : null}
            {t.message ? <div className="mt-1 text-sm text-slate-600">{t.message}</div> : null}
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

export default ToastProvider;
