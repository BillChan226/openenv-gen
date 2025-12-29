import { getOrCreateCart } from './sessionStore.js';
import { getProductById } from './dataService.js';
import { ApiError } from '../middleware/errorHandler.js';

export async function getCart(userId) {
  const cart = getOrCreateCart(userId);
  return hydrateCart(cart);
}

export async function addToCart(userId, productId, quantity = 1) {
  const cart = getOrCreateCart(userId);
  const qty = Math.max(1, Number(quantity) || 1);
  const existing = cart.items.find((i) => i.productId === productId);
  if (existing) existing.quantity += qty;
  else cart.items.push({ productId, quantity: qty });
  return hydrateCart(cart);
}

export async function updateCartItem(userId, productId, quantity) {
  const cart = getOrCreateCart(userId);
  const qty = Number(quantity);
  const idx = cart.items.findIndex((i) => i.productId === productId);
  if (idx === -1) throw ApiError.notFound('Cart item not found');
  if (!Number.isFinite(qty) || qty <= 0) {
    cart.items.splice(idx, 1);
  } else {
    cart.items[idx].quantity = Math.floor(qty);
  }
  return hydrateCart(cart);
}

export async function removeCartItem(userId, productId) {
  const cart = getOrCreateCart(userId);
  cart.items = cart.items.filter((i) => i.productId !== productId);
  return hydrateCart(cart);
}

export async function clearCart(userId) {
  const cart = getOrCreateCart(userId);
  cart.items = [];
  return hydrateCart(cart);
}

function toCents(amount) {
  // Convert a JS number price (e.g., 49.99) to integer cents safely.
  return Math.round(Number(amount) * 100);
}

function fromCents(cents) {
  // Return a number rounded to 2 decimals.
  return Math.round(Number(cents)) / 100;
}

async function hydrateCart(cart) {
  const hydratedItems = [];
  let subtotalCents = 0;
  let itemCount = 0;

  for (const item of cart.items) {
    const product = await getProductById(item.productId);
    if (!product) continue;

    const priceCents = toCents(product.price);
    const lineTotalCents = priceCents * item.quantity;

    subtotalCents += lineTotalCents;
    itemCount += item.quantity;

    hydratedItems.push({
      productId: item.productId,
      quantity: item.quantity,
      product,
      lineTotal: fromCents(lineTotalCents)
    });
  }

  return {
    items: hydratedItems,
    itemCount,
    subtotal: fromCents(subtotalCents)
  };
}
