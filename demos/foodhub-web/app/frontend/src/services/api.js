import http from './apiClient';
import { unwrapItems, unwrapResponse } from '../utils/unwrap';

// ---- Health ----
export async function health() {
  const res = await http.get('/api/health');
  return unwrapResponse(res);
}

// ---- Auth ----
export async function login(payload) {
  const res = await http.post('/api/auth/login', payload);
  return unwrapResponse(res);
}

export async function register(payload) {
  const res = await http.post('/api/auth/register', payload);
  return unwrapResponse(res);
}

export async function me() {
  const res = await http.get('/api/auth/me');
  return unwrapResponse(res);
}

// Alias used by ProfilePage
export const getMe = me;

// ---- Restaurants ----
export async function getRestaurantCategories(params) {
  const res = await http.get('/api/restaurant-categories', { params });
  return unwrapItems(res);
}

export async function getRestaurants(params) {
  const res = await http.get('/api/restaurants', { params });
  return unwrapItems(res);
}

export async function getRestaurantById(id) {
  const res = await http.get(`/api/restaurants/${id}`);
  return unwrapResponse(res);
}

export async function getRestaurantMenu(id) {
  const res = await http.get(`/api/restaurants/${id}/menu`);
  return unwrapResponse(res);
}

// ---- Search ----
export async function getSearchSuggestions(params) {
  const res = await http.get('/api/search/suggestions', { params });
  return unwrapItems(res);
}

// ---- Favorites ----
export async function getFavorites(params) {
  const res = await http.get('/api/favorites', { params });
  return unwrapItems(res);
}

export async function addFavorite(restaurantId) {
  const res = await http.post('/api/favorites', { restaurantId });
  return unwrapResponse(res);
}

export async function removeFavorite(restaurantId) {
  const res = await http.delete(`/api/favorites/${restaurantId}`);
  return unwrapResponse(res);
}

// ---- Cart ----
export async function getCart() {
  const res = await http.get('/api/cart');
  return unwrapResponse(res);
}

export async function clearCart() {
  const res = await http.delete('/api/cart');
  return unwrapResponse(res);
}

export async function addToCart(payload) {
  // payload: { restaurantId, menuItemId, quantity, selectedModifierOptionIds?, notes? }
  const res = await http.post('/api/cart/items', payload);
  return unwrapResponse(res);
}

export async function updateCartItem(cartItemId, payload) {
  const res = await http.patch(`/api/cart/items/${cartItemId}`, payload);
  return unwrapResponse(res);
}

export async function removeCartItem(cartItemId) {
  const res = await http.delete(`/api/cart/items/${cartItemId}`);
  return unwrapResponse(res);
}

export async function applyPromoCode(code) {
  const res = await http.post('/api/cart/promo', { code });
  return unwrapResponse(res);
}

// ---- Profile ----
export async function getAddresses() {
  const res = await http.get('/api/profile/addresses');
  return unwrapItems(res);
}

export async function createAddress(payload) {
  const res = await http.post('/api/profile/addresses', payload);
  return unwrapResponse(res);
}

export async function getPaymentMethods() {
  const res = await http.get('/api/profile/payment-methods');
  return unwrapItems(res);
}

export async function createPaymentMethod(payload) {
  const res = await http.post('/api/profile/payment-methods', payload);
  return unwrapResponse(res);
}

// ---- Orders ----
export async function createOrder(payload) {
  const res = await http.post('/api/orders', payload);
  return unwrapResponse(res);
}

export async function getOrders(params) {
  const res = await http.get('/api/orders', { params });
  return unwrapItems(res);
}

export async function getOrderById(orderId) {
  const res = await http.get(`/api/orders/${orderId}`);
  return unwrapResponse(res);
}

export async function reorder(orderId) {
  const res = await http.post(`/api/orders/${orderId}/reorder`);
  return unwrapResponse(res);
}

// Aliases to avoid import mismatches
export const fetchRestaurants = getRestaurants;
export const listRestaurants = getRestaurants;
export const searchRestaurants = getRestaurants;
export const listOrders = getOrders;
export const fetchOrders = getOrders;

export const getRestaurant = getRestaurantById;
export const listRestaurantProducts = getRestaurantMenu;

export const reorderOrder = reorder;
