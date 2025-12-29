import { getOrCreateWishlist } from './sessionStore.js';
import { getProductById } from './dataService.js';

export async function getWishlist(userId) {
  const wl = getOrCreateWishlist(userId);
  return hydrate(wl);
}

export async function toggleWishlist(userId, productId) {
  const wl = getOrCreateWishlist(userId);
  const idx = wl.productIds.indexOf(productId);
  if (idx >= 0) wl.productIds.splice(idx, 1);
  else wl.productIds.push(productId);
  return hydrate(wl);
}

export async function removeFromWishlist(userId, productId) {
  const wl = getOrCreateWishlist(userId);
  wl.productIds = wl.productIds.filter((id) => id !== productId);
  return hydrate(wl);
}

async function hydrate(wl) {
  const items = [];
  for (const id of wl.productIds) {
    const product = await getProductById(id);
    if (product) items.push(product);
  }
  return { items, productIds: [...wl.productIds] };
}
