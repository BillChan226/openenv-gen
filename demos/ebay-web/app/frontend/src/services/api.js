const API_URL = import.meta.env.VITE_API_URL || '/api';
const TOKEN_KEY = 'auth_token';

function getToken() {
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
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(res) {
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await res.json().catch(() => null) : await res.text().catch(() => null);

  if (!res.ok) {
    const message =
      (payload && typeof payload === 'object' && (payload.message || payload.error?.message)) ||
      (typeof payload === 'string' && payload) ||
      res.statusText ||
      `HTTP ${res.status}`;
    const err = new Error(message);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }

  return payload;
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: buildHeaders({ json: body !== undefined, auth }),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse(res);
}

// Auth
export async function login(email, password) {
  try {
    const data = await request('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
    if (data?.token) setAuthToken(data.token);
    return data;
  } catch (e) {
    // Demo/static mode fallback: accept the demo credentials.
    if (e?.status === 404 && email === 'demo@ebay.local' && password === 'demo') {
      const data = { token: 'demo-token', user: { email, name: 'Demo User' } };
      setAuthToken(data.token);
      return data;
    }
    throw e;
  }
}

export function logout() {
  // Backend may support /auth/logout; client-side token clear is primary
  setAuthToken(null);
}

export async function getMe() {
  try {
    return await request('/auth/me');
  } catch (e) {
    // In demo/static mode the backend may not be running.
    if (e?.status === 404) return null;
    throw e;
  }
}

// Catalog
export async function listProducts(params = {}) {
  // Filter out undefined/null values to avoid sending "undefined" as literal string
  const filtered = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  );
  const query = new URLSearchParams(filtered).toString();
  return request(`/products${query ? `?${query}` : ''}`, { method: 'GET', auth: false });
}

export async function getProduct(id) {
  return request(`/products/${encodeURIComponent(id)}`, { method: 'GET', auth: false });
}

export async function getCategoriesTree() {
  // Prefer /categories, fallback to /categories/tree
  try {
    return await request('/categories', { method: 'GET', auth: false });
  } catch (_e) {
    return request('/categories/tree', { method: 'GET', auth: false });
  }
}

export async function getCategoryBySlug(slug) {
  return request(`/categories/${encodeURIComponent(slug)}`, { method: 'GET', auth: false });
}

export async function listCategoryProducts(slug, params = {}) {
  // Filter out undefined/null values to avoid sending "undefined" as literal string
  const filtered = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  );
  const query = new URLSearchParams(filtered).toString();
  return request(`/categories/${encodeURIComponent(slug)}/products${query ? `?${query}` : ''}`, {
    method: 'GET',
    auth: false,
  });
}

// Advanced search
export async function advancedSearch(body) {
  return request('/search/advanced', { method: 'POST', body, auth: false });
}

// Cart
export async function getCart() {
  return request('/cart');
}

export async function addCartItem(productId, quantity = 1) {
  return request('/cart/items', { method: 'POST', body: { productId, quantity } });
}

export async function updateCartItem(productId, quantity) {
  // Backend supports PATCH
  try {
    return await request('/cart/items', { method: 'PATCH', body: { productId, quantity } });
  } catch (_e) {
    return request(`/cart/items/${encodeURIComponent(productId)}`, { method: 'PATCH', body: { quantity } });
  }
}

export async function removeCartItem(productId) {
  // Support both body and path-param styles
  try {
    return await request(`/cart/items/${encodeURIComponent(productId)}`, { method: 'DELETE' });
  } catch (_e) {
    return request('/cart/items', { method: 'DELETE', body: { productId } });
  }
}

// Wishlist
export async function getWishlist() {
  return request('/wishlist');
}

export async function toggleWishlist(productId) {
  return request('/wishlist/toggle', { method: 'POST', body: { productId } });
}

export async function addWishlistItem(productId) {
  try {
    return await request('/wishlist/items', { method: 'POST', body: { productId } });
  } catch {
    return toggleWishlist(productId);
  }
}

export async function removeWishlistItem(productId) {
  try {
    return await request(`/wishlist/items/${encodeURIComponent(productId)}`, { method: 'DELETE' });
  } catch {
    return request('/wishlist/items', { method: 'DELETE', body: { productId } });
  }
}

// Account
export async function getAccountOverview() {
  try {
    return await request('/account');
  } catch {
    return request('/account/me');
  }
}

export async function getAccountOrders() {
  return request('/account/orders');
}

export async function getAccountAddresses() {
  return request('/account/addresses');
}
