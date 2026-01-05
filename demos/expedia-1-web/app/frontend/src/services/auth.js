import { getItem, postItem } from './api';

const TOKEN_KEY = 'voyager_access_token';
const USER_KEY = 'voyager_user_cache';
const USER_TTL_MS = 5 * 60 * 1000;

export function getAccessToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // ignore
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // ignore
  }
}

export function getCachedMe() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.user || !parsed?.ts) return null;
    if (Date.now() - parsed.ts > USER_TTL_MS) return null;
    return parsed.user;
  } catch {
    return null;
  }
}

export function setCachedMe(user) {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify({ user, ts: Date.now() }));
  } catch {
    // ignore
  }
}

export async function login({ email, password }) {
  // API_BASE already includes '/api' by default; keep paths relative to it.
  // Backend expects POST /api/auth/login.
  const item = await postItem('/auth/login', { email, password });

  // Support multiple backend response shapes.
  // Expected: { access_token, user }
  // Also accept: { token }, { accessToken }, or nested wrappers.
  const token =
    item?.access_token ||
    item?.token ||
    item?.accessToken ||
    item?.data?.access_token ||
    item?.data?.token ||
    item?.item?.access_token ||
    item?.item?.token;

  if (token) setAccessToken(token);

  const user = item?.user || item?.data?.user || item?.item?.user;
  if (user) setCachedMe(user);

  return item;
}

export async function register({ email, password, name, phone }) {
  const item = await postItem('/auth/register', { email, password, name, phone });

  const token =
    item?.access_token ||
    item?.token ||
    item?.accessToken ||
    item?.data?.access_token ||
    item?.data?.token ||
    item?.item?.access_token ||
    item?.item?.token;

  if (token) setAccessToken(token);

  const user = item?.user || item?.data?.user || item?.item?.user;
  if (user) setCachedMe(user);

  return item;
}

export async function me() {
  const cached = getCachedMe();
  if (cached) return { user: cached };
  const item = await getItem('/auth/me');
  if (item?.user) setCachedMe(item.user);
  return item;
}

export async function logout() {
  try {
    await postItem('/auth/logout');
  } catch {
    // ignore
  } finally {
    clearSession();
  }
}
