import React from 'react';

const ToastCtx = React.createContext(null);

export function useToast() {
  const ctx = React.useContext(ToastCtx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = React.useState([]);

  const push = React.useCallback((toast) => {
    const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`;
    const t = {
      id,
      title: toast?.title || 'Notice',
      message: toast?.message || '',
      variant: toast?.variant || 'info',
      ttl: toast?.ttl ?? 3500
    };
    setToasts((prev) => [t, ...prev].slice(0, 4));
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, t.ttl);
  }, []);

  const api = React.useMemo(() => ({ push }), [push]);

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[92vw] max-w-sm flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={
              'pointer-events-auto rounded-2xl border bg-white p-4 shadow-dropdown ring-1 ' +
              (t.variant === 'success'
                ? 'border-emerald-200 ring-emerald-100'
                : t.variant === 'error'
                  ? 'border-red-200 ring-red-100'
                  : 'border-slate-200 ring-slate-100')
            }
          >
            <div className="text-sm font-semibold text-slate-900">{t.title}</div>
            {t.message ? <div className="mt-1 text-sm text-slate-600">{t.message}</div> : null}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
