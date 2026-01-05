import { http, unwrapItem, unwrapList } from './apiClient';

// ---------- Auth ----------
export async function login(payload) {
  const res = await http.post('/auth/login', payload);
  // handle {token, user} or {data:{token,user}}
  return res.data;
}

export async function register(payload) {
  const res = await http.post('/auth/register', payload);
  return res.data;
}

export async function getMe() {
  const res = await http.get('/auth/me');
  return unwrapItem(res.data);
}

// Backwards-compatible aliases (some pages may use /api/auth/*)
export const apiLogin = login;
export const apiRegister = register;

// ---------- Locations ----------
export async function searchLocations(params) {
  const res = await http.get('/locations', { params });
  return unwrapList(res.data);
}

// ---------- Flights ----------
export async function searchFlights(params) {
  const res = await http.get('/flights', { params });
  return unwrapList(res.data);
}
export const getFlights = searchFlights;
export const fetchFlights = searchFlights;

export async function getFlightById(flightId) {
  const res = await http.get(`/flights/${flightId}`);
  return unwrapItem(res.data);
}

// ---------- Hotels ----------
export async function searchHotels(params) {
  const res = await http.get('/hotels', { params });
  return unwrapList(res.data);
}
export const getHotels = searchHotels;
export const fetchHotels = searchHotels;

export async function getHotelById(hotelId) {
  const res = await http.get(`/hotels/${hotelId}`);
  return unwrapItem(res.data);
}

export async function getHotelRooms(hotelId, params) {
  const res = await http.get(`/hotels/${hotelId}/rooms`, { params });
  return unwrapList(res.data);
}


// Alias used by older pages
export const listHotelRooms = getHotelRooms;

// ---------- Cars ----------
export async function searchCars(params) {
  const res = await http.get('/cars', { params });
  return unwrapList(res.data);
}
export const getCars = searchCars;
export const fetchCars = searchCars;

export async function getCarById(carId) {
  const res = await http.get(`/cars/${carId}`);
  return unwrapItem(res.data);
}

// ---------- Packages ----------
export async function searchPackages(params) {
  const res = await http.get('/packages', { params });
  return unwrapList(res.data);
}
export const getPackages = searchPackages;

export async function getPackageById(packageId) {
  const res = await http.get(`/packages/${packageId}`);
  return unwrapItem(res.data);
}

// ---------- Favorites ----------
export async function getFavorites() {
  const res = await http.get('/favorites');
  return unwrapList(res.data);
}

export async function addFavorite(payload) {
  const res = await http.post('/favorites', payload);
  return unwrapItem(res.data);
}

export async function removeFavorite(favoriteId) {
  const res = await http.delete(`/favorites/${favoriteId}`);
  return res.data;
}

// ---------- Cart ----------
export async function getCart() {
  const res = await http.get('/cart');
  return unwrapItem(res.data);
}

export async function addToCart(payload) {
  const res = await http.post('/cart/items', payload);
  return unwrapItem(res.data);
}

export async function updateCartItem(cartItemId, payload) {
  const res = await http.patch(`/cart/items/${cartItemId}`, payload);
  return unwrapItem(res.data);
}

export async function removeCartItem(cartItemId) {
  const res = await http.delete(`/cart/items/${cartItemId}`);
  return res.data;
}

export async function clearCart() {
  const res = await http.delete('/cart');
  return res.data;
}

export async function applyPromoCode(payload) {
  const res = await http.post('/cart/promo', payload);
  return unwrapItem(res.data);
}

// ---------- Checkout ----------
export async function checkout(payload) {
  const res = await http.post('/checkout', payload);
  return unwrapItem(res.data);
}
export const checkoutCart = checkout;

// ---------- Trips / Orders ----------
export async function getTrips(params) {
  const res = await http.get('/trips', { params });
  return unwrapList(res.data);
}
export const listTrips = getTrips;

export async function getTripById(tripId) {
  const res = await http.get(`/trips/${tripId}`);
  return unwrapItem(res.data);
}

export async function cancelTrip(tripId) {
  const res = await http.post(`/trips/${tripId}/cancel`);
  return unwrapItem(res.data);
}

// ---------- Profile ----------
export async function updateProfile(payload) {
  const res = await http.patch('/users/me', payload);
  return unwrapItem(res.data);
}

export async function listPaymentMethods() {
  const res = await http.get('/users/me/payment-methods');
  return unwrapList(res.data);
}

export async function addPaymentMethod(payload) {
  const res = await http.post('/users/me/payment-methods', payload);
  return unwrapItem(res.data);
}

export async function deletePaymentMethod(paymentMethodId) {
  const res = await http.delete(`/users/me/payment-methods/${paymentMethodId}`);
  return res.data;
}
