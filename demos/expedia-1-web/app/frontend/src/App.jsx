import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AuthProvider from './context/AuthContext.jsx';
import ToastProvider from './components/ui/ToastProvider.jsx';
import AppShell from './components/layout/AppShell.jsx';
import Home from './pages/Home.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';

function ServiceBanner({ status }) {
  if (!status) return null;

  const { apiOk, apiUrl, error } = status;
  if (apiOk) return null;

  return (
    <div
      style={{
        padding: '12px 16px',
        background: '#fff4e5',
        borderBottom: '1px solid #ffd7a8',
        color: '#5a3b00'
      }}
      role="alert"
    >
      <strong>Backend API unreachable.</strong>{' '}
      <span>
        The UI is running, but requests to <code>{apiUrl}</code> are failing.
      </span>
      {error ? (
        <div style={{ marginTop: 6, fontSize: 12, opacity: 0.9 }}>{String(error)}</div>
      ) : null}
      <div style={{ marginTop: 8, fontSize: 12 }}>
        Start services with: <code>docker compose up --build</code> (from <code>generated/expedia/docker</code>)
      </div>
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      // Use the same base as api.js (defaults to '/api')
      // IMPORTANT: In Vite, only variables prefixed with VITE_ are exposed to the client.
      // Prefer same-origin relative '/api' so the UI remains reachable in preview/Docker.
      const apiBaseRaw =
        import.meta.env.VITE_API_BASE ||
        import.meta.env.VITE_API_BASE_URL ||
        import.meta.env.API_BASE ||
        '/api';
      const apiBase = apiBaseRaw.startsWith('http') ? apiBaseRaw.replace(/\/$/, '') : apiBaseRaw;
      const apiUrl = `${apiBase}/health`;

      try {
        const res = await fetch(apiUrl, { headers: { Accept: 'application/json' } });
        if (!cancelled) setStatus({ apiOk: res.ok, apiUrl });
      } catch (e) {
        if (!cancelled) setStatus({ apiOk: false, apiUrl, error: e?.message || e });
      }
    }

    check();
    const t = setInterval(check, 8000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <ToastProvider>
      <AuthProvider>
        <ServiceBanner status={status} />
        <AppShell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/stays" element={<Home initialTab="stays" />} />
            <Route path="/flights" element={<Home initialTab="flights" />} />
            <Route path="/cars" element={<Home initialTab="cars" />} />
            <Route path="/packages" element={<Home initialTab="packages" />} />
            <Route path="/search" element={<Home />} />
            <Route path="/cart" element={<Home />} />
            <Route path="/account" element={<Home />} />
            <Route path="/trips" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </AuthProvider>
    </ToastProvider>
  );
}
