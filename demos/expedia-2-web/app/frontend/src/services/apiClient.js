import axios from 'axios';

// Use relative base URL so the dev server/nginx can proxy API calls.
// IMPORTANT: keep API under /api to avoid conflicts with React Router routes.
// IMPORTANT: Always use relative '/api' baseURL in the browser so Vite/nginx can proxy.
// If someone sets VITE_API_BASE_URL to an absolute URL (e.g. http://localhost:8082),
// it will bypass the proxy and may hit non-/api routes.
const baseURL = '/api';

export const http = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Initialize auth header from persisted token (prevents first-load 401s before AuthProvider effect runs)
try {
  const storedToken = localStorage.getItem('auth_token');
  if (storedToken) {
    // We can set the header directly here as well.
    http.defaults.headers.common.Authorization = `Bearer ${storedToken}`;
  }
} catch {
  // ignore (e.g., SSR / restricted storage)
}


export function setAuthToken(token) {
  if (token) {
    http.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete http.defaults.headers.common.Authorization;
  }
}

export function unwrapList(data) {
  if (!data) return [];
  return data.items || data.results || data;
}

export function unwrapItem(data) {
  if (!data) return null;

  // Common API shapes:
  // - { item: {...} }
  // - { data: {...} }
  // - { cart: {...} }, { flight: {...} }, { hotel: {...} } (single-key wrapper)
  if (data.item) return data.item;
  if (data.data) return data.data;

  if (typeof data === 'object' && !Array.isArray(data)) {
    const keys = Object.keys(data);
    if (keys.length === 1) return data[keys[0]];
  }

  return data;
}
