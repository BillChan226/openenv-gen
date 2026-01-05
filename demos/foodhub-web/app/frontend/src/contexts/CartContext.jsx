import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';

const CartContext = createContext(null);

function normalizeApiError(err) {
  const status = err?.response?.status;
  const payload = err?.response?.data;
  const code = payload?.error?.code;
  const message = payload?.error?.message || err?.message;
  return { status, code, message, payload };
}

export function CartProvider({ children }) {
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refreshCart = useCallback(async () => {
    // Guest sessions should not call /api/cart (backend returns 401).
    const token = localStorage.getItem('fh_token');
    if (!token) {
      setCart(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const data = await api.getCart();
      setCart(data?.cart || data || null);
    } catch (err) {
      const status = err?.response?.status;
      // Treat unauthenticated cart fetch as expected state.
      if (status === 401) {
        setCart(null);
      } else {
        // Avoid crashing app on transient errors.
        setCart((prev) => prev || null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const clear = useCallback(async () => {
    await api.clearCart();
    await refreshCart();
  }, [refreshCart]);

  const addItem = useCallback(
    async ({ restaurantId, menuItemId, quantity = 1, selectedModifierOptionIds = [], notes = '' }) => {
      try {
        const payload = { restaurantId, menuItemId, quantity, selectedModifierOptionIds };
        if (notes) payload.notes = notes;
        await api.addToCart(payload);
        await refreshCart();
        setDrawerOpen(true);
        return { ok: true };
      } catch (err) {
        const e = normalizeApiError(err);
        // Backend enforces single-restaurant cart.
        // If mismatch, return error so UI can prompt user to clear cart.
        if (e?.status === 409 && e?.code === 'CART_RESTAURANT_MISMATCH') {
          return { ok: false, conflict: true, error: e };
        }
        return { ok: false, error: e };
      }
    },
    [refreshCart]
  );

  const updateItem = useCallback(
    async (cartItemId, patch) => {
      await api.updateCartItem(cartItemId, patch);
      await refreshCart();
    },
    [refreshCart]
  );

  const removeItem = useCallback(
    async (cartItemId) => {
      await api.removeCartItem(cartItemId);
      await refreshCart();
    },
    [refreshCart]
  );

  const applyPromo = useCallback(
    async (code) => {
      await api.applyPromoCode(code);
      await refreshCart();
    },
    [refreshCart]
  );

  const value = useMemo(() => {
    const pricing = cart?.pricing || {};
    const itemCount = pricing.itemCount || 0;
    return {
      cart,
      loading,
      itemCount,
      drawerOpen,
      setDrawerOpen,
      refreshCart,
      clear,
      addItem,
      updateItem,
      removeItem,
      applyPromo
    };
  }, [cart, loading, drawerOpen, refreshCart, clear, addItem, updateItem, removeItem, applyPromo]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}

export default CartContext;
