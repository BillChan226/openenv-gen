// Simple in-memory stores.
// For demo purposes only.

const cartsByUser = new Map();
const wishlistByUser = new Map();

// JWT session store keyed by jti
// { userId, createdAt, expiresAt, revokedAt }
const jwtSessionsByJti = new Map();

export function getOrCreateCart(userId) {
  if (!cartsByUser.has(userId)) {
    cartsByUser.set(userId, { items: [] });
  }
  return cartsByUser.get(userId);
}

export function getOrCreateWishlist(userId) {
  if (!wishlistByUser.has(userId)) {
    wishlistByUser.set(userId, { productIds: [] });
  }
  return wishlistByUser.get(userId);
}

export function clearUserSessionData(userId) {
  cartsByUser.delete(userId);
  wishlistByUser.delete(userId);
}

export function createJwtSession({ jti, userId, expiresAt }) {
  jwtSessionsByJti.set(jti, {
    userId,
    createdAt: Date.now(),
    expiresAt,
    revokedAt: null
  });
}

export function getJwtSession(jti) {
  return jwtSessionsByJti.get(jti);
}

export function revokeJwtSession(jti) {
  const session = jwtSessionsByJti.get(jti);
  if (!session) return false;
  session.revokedAt = Date.now();
  jwtSessionsByJti.set(jti, session);
  return true;
}

export function isJwtSessionActive(jti) {
  const session = jwtSessionsByJti.get(jti);
  // Return null when the store has no knowledge of this jti.
  // Callers can treat that as "unknown" and fall back to stateless JWT validation.
  if (!session) return null;
  if (session.revokedAt) return false;
  if (typeof session.expiresAt === 'number' && session.expiresAt <= Date.now()) return false;
  return true;
}
