import { getAccessToken, clearSession } from './auth';

// Use relative '/api' by default (works with Vite proxy / same-origin deployments).
// Allow override for environments where the frontend is served separately.
// IMPORTANT: In Vite, only variables prefixed with VITE_ are exposed to the client.
// Some environments may provide API_BASE without the prefix; fall back gracefully.
// Prefer same-origin relative '/api' to work in Docker/preview environments.
// Allow absolute override via VITE_API_BASE (or legacy API_BASE).
//
// NOTE: Callers should pass paths *relative to* API_BASE (e.g. '/auth/login'),
// which will resolve to '/api/auth/login' by default.
// Support both VITE_API_BASE (expected) and older VITE_API_BASE_URL naming.
const API_BASE_RAW =
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.API_BASE ||
  // Some environments provide a full origin without the '/api' prefix.
  // Default to same-origin '/api' to match backend routes.
  '/api';

// If API_BASE is set to an origin (e.g. http://localhost:8080), automatically
// append '/api' so callers can keep using relative paths like '/auth/login'.
// This prevents accidental calls to '/auth/login' on the origin which would 404.
const API_BASE_NORMALIZED = (() => {
  if (API_BASE_RAW.startsWith('http')) {
    const trimmed = API_BASE_RAW.replace(/\/$/, '');
    return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
  }
  return API_BASE_RAW;
})();

const API_BASE = API_BASE_NORMALIZED.replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function toQuery(params = {}) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    if (Array.isArray(v)) {
      if (v.length === 0) return;
      usp.set(k, v.join(','));
      return;
    }
    usp.set(k, String(v));
  });
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {})
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers
    });
  } catch (e) {
    // Network errors (e.g. backend down, DNS, CORS) won't produce a Response.
    // Surface a consistent ApiError so UI can show feedback.
    throw new ApiError('Network error: unable to reach the server', {
      status: 0,
      code: 'NETWORK_ERROR',
      details: e?.message || String(e)
    });
  }

  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await res.json().catch(() => null) : await res.text().catch(() => null);

  if (!res.ok) {
    if (res.status === 401) {
      clearSession();
    }

    // Support multiple backend error shapes.
    // Preferred: { error: { message, code, details } }
    // Also accept: { message }, { error: '...' }, { error: { userMessage } }
    const err = data?.error;

    const backendUserMessage =
      (typeof err?.details?.userMessage === 'string' && err.details.userMessage.trim()) ||
      (typeof err?.userMessage === 'string' && err.userMessage.trim()) ||
      (typeof data?.userMessage === 'string' && data.userMessage.trim()) ||
      null;

    const backendMessage =
      (typeof err?.message === 'string' && err.message.trim()) ||
      (typeof data?.message === 'string' && data.message.trim()) ||
      (typeof err === 'string' && err.trim()) ||
      null;

    const message =
      backendUserMessage ||
      backendMessage ||
      (res.status === 404
        ? 'Endpoint not found (404). Is the backend running?'
        : res.status === 503
          ? 'Service temporarily unavailable. Please try again in a moment.'
          : `Request failed (${res.status})`);

    throw new ApiError(message, {
      status: res.status,
      code: err?.code,
      details: err?.details
    });
  }

  return data;
}

export async function getList(path, params, options) {
  const data = await request(`${path}${toQuery(params)}`, options);
  return data?.items ?? [];
}

export async function getItem(path, params, options) {
  const data = await request(`${path}${toQuery(params)}`, options);
  return data?.item ?? null;
}

export async function postItem(path, body, options) {
  const data = await request(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
    ...options
  });

  // Many endpoints return { item: ... }, but auth endpoints may return a top-level
  // payload like { access_token, user }. If there's no wrapper, return the raw data.
  return data?.item ?? data;
}

export async function patchItem(path, body, options) {
  const data = await request(path, {
    method: 'PATCH',
    body: body ? JSON.stringify(body) : undefined,
    ...options
  });
  return data?.item ?? null;
}

export async function deleteItem(path, options) {
  const data = await request(path, {
    method: 'DELETE',
    ...options
  });
  return data?.item ?? null;
}
