// Base URL for API requests.
// - In local dev, default to '/api' so Vite proxy can forward to the backend.
// - In Docker/prod-like deployments, keep '/api' and let the web server reverse-proxy.
// - If you need an absolute URL (e.g., running frontend separately), set VITE_API_BASE_URL.
const API_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api';
const TOKEN_KEY = 'auth_token';

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function buildHeaders({ json = true, auth = true } = {}) {
  const headers = {};
  if (json) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = getAuthToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseError(res) {
  const data = await res.json().catch(() => null);
  if (!data) return { message: res.statusText };

  // Support both {error:{code,message}} and {error:'validation_error',message}
  if (data.error && typeof data.error === 'object') {
    return { message: data.error.message || data.message || res.statusText, details: data.error.details };
  }
  return { message: data.message || data.error || res.statusText, details: data.details };
}

async function handleResponse(res) {
  if (!res.ok) {
    const err = await parseError(res);
    const e = new Error(err.message || `HTTP ${res.status}`);
    e.details = err.details;
    e.status = res.status;
    throw e;
  }
  if (res.status === 204) return null;
  return res.json();
}

async function request(path, { method = 'GET', body, auth = true, signal, retry = 0 } = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: buildHeaders({ json: body !== undefined, auth }),
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
    signal,
  });

  // Never retry on 429 (rate limited). Surface the error to the UI.
  if (res.status === 429) {
    return handleResponse(res);
  }

  // Optional lightweight retry for transient errors (network/5xx) with small backoff.
  if (retry > 0 && (res.status >= 500 || res.status === 0)) {
    await new Promise((r) => setTimeout(r, 250));
    return request(path, { method, body, auth, signal, retry: retry - 1 });
  }

  return handleResponse(res);
}

// Auth
export async function login(email, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });

  if (data?.token) setAuthToken(data.token);
  return data;
}

export async function getMe() {
  return request('/auth/me');
}

export async function logout() {
  try {
    await request('/auth/logout', { method: 'POST' });
  } finally {
    setAuthToken(null);
  }
}

// Projects
export async function getProjects() {
  return request('/projects');
}

export async function getProjectByKey(projectKey) {
  return request(`/projects/${encodeURIComponent(projectKey)}`);
}

export async function createProject(payload) {
  return request('/projects', { method: 'POST', body: payload });
}

// Users
export async function getUsers() {
  return request('/users');
}

// Issues
export async function getIssues(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/issues${query ? `?${query}` : ''}`);
}

export async function getIssueById(issueId) {
  return request(`/issues/${encodeURIComponent(issueId)}`);
}

export async function createIssue(payload) {
  return request('/issues', { method: 'POST', body: payload });
}

export async function updateIssue(issueId, payload) {
  return request(`/issues/${encodeURIComponent(issueId)}`, { method: 'PATCH', body: payload });
}

export async function updateIssueStatus(issueId, status) {
  return request(`/issues/${encodeURIComponent(issueId)}/status`, { method: 'PATCH', body: { status } });
}

export async function getIssueHistory(issueId) {
  return request(`/issues/${encodeURIComponent(issueId)}/history`);
}

// Comments
export async function getIssueComments(issueId) {
  return request(`/comments?issueId=${encodeURIComponent(issueId)}`);
}

export async function addIssueComment(issueId, body) {
  return request(`/comments`, { method: 'POST', body: { issueId, bodyMarkdown: body } });
}

export async function updateComment(commentId, body) {
  return request(`/comments/${encodeURIComponent(commentId)}`, { method: 'PATCH', body: { body } });
}

export async function deleteComment(commentId) {
  return request(`/comments/${encodeURIComponent(commentId)}`, { method: 'DELETE' });
}

// Search (backend currently GET /search?q=...)
export async function search({ q, projectKey, status, assigneeId } = {}) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (projectKey) params.set('projectKey', projectKey);
  if (status) params.set('status', status);
  if (assigneeId) params.set('assigneeId', assigneeId);
  return request(`/search?${params.toString()}`);
}

// Settings
export async function getSettings() {
  return request('/settings');
}

export async function updateSettings(payload) {
  // Support both PUT and PATCH; prefer PUT since backend has it
  return request('/settings', { method: 'PUT', body: payload });
}
