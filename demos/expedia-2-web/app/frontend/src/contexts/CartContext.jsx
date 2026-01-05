import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  addToCart as apiAddToCart,
  applyPromoCode as apiApplyPromoCode,
  clearCart as apiClearCart,
  getCart as apiGetCart,
  removeCartItem as apiRemoveCartItem,
  updateCartItem as apiUpdateCartItem
} from '../services/api';
import { useAuth } from './AuthContext';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { isAuthed } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refreshCart = useCallback(async () => {
    if (!isAuthed) {
      setCart(null);
      return null;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await apiGetCart();
      setCart(next);
      return next;
    } catch (e) {
      setError(e);
      return null;
    } finally {
      setLoading(false);
    }
  }, [isAuthed]);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const mapUiItemToApiPayload = useCallback((input) => {
    // Supports both UI-friendly shapes (used by detail pages) and already-correct API payloads.
    // UI shape example: { type:'flight', id:'FL_001', passengers:1 }
    // API shape example: { item_type:'flight', flight_id:'FL_001', passengers:1 }
    if (!input || typeof input !== 'object') return input;

    // If it already looks like an API payload, pass through.
    if (input.item_type) return input;

    const type = input.type || input.itemType;
    const id = input.id || input.flight_id || input.hotel_id || input.car_id || input.package_id;

    if (!type) return input;

    switch (type) {
      case 'flight':
        return {
          item_type: 'flight',
          flight_id: input.flight_id || id,
          passengers: Number(input.passengers ?? input.qty ?? 1)
        };
      case 'hotel':
      case 'hotel_room':
        return {
          item_type: 'hotel',
          hotel_id: input.hotel_id || input.payload?.hotel?.id || id,
          hotel_room_id: input.hotel_room_id || input.room_id || input.roomId || input.payload?.room?.id,
          rooms: Number(input.rooms ?? input.qty ?? 1),
          guests: Number(input.guests ?? 2),
          start_date: input.start_date || input.check_in || input.checkIn,
          end_date: input.end_date || input.check_out || input.checkOut,
          extras: input.extras
        };
      case 'car':
        return {
          item_type: 'car',
          car_id: input.car_id || id,
          start_date: input.start_date || input.pickup_date || input.pickupDate,
          end_date: input.end_date || input.dropoff_date || input.dropoffDate,
          extras: input.extras
        };
      case 'package':
        return {
          item_type: 'package',
          package_id: input.package_id || id,
          passengers: Number(input.passengers ?? input.travelers ?? 1),
          extras: input.extras
        };
      default:
        return input;
    }
  }, []);

  const addToCart = useCallback(
    async (payloadOrUiItem) => {
      setLoading(true);
      setError(null);
      try {
        const payload = mapUiItemToApiPayload(payloadOrUiItem);
        await apiAddToCart(payload);
        // Always refresh from backend so UI matches server truth.
        const next = await apiGetCart();
        setCart(next);
        return next;
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [mapUiItemToApiPayload]
  );

  const updateItem = useCallback(
    async (cartItemId, payload) => {
      setLoading(true);
      setError(null);
      try {
        await apiUpdateCartItem(cartItemId, payload);
        return await refreshCart();
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [refreshCart]
  );

  const removeItem = useCallback(async (cartItemId) => {
    setLoading(true);
    setError(null);
    try {
      await apiRemoveCartItem(cartItemId);
      return await refreshCart();
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [refreshCart]);

  const clear = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await apiClearCart();
      return await refreshCart();
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [refreshCart]);

  const applyPromo = useCallback(async (code) => {
    setLoading(true);
    setError(null);
    try {
      const next = await apiApplyPromoCode({ code });
      setCart(next);
      return next;
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  // Backwards-compatible aliases: some pages/components expect addItem/clearCart/etc.
  // NOTE: We intentionally provide multiple names to avoid runtime `xxx is not a function`
  // when pages were implemented against older context APIs.
  const addItem = addToCart;
  const add = addToCart;
  const addLineItem = addToCart;
  const clearCart = clear;

  const value = useMemo(
    () => ({
      cart,
      loading,
      error,
      refreshCart,
      // Primary names
      addToCart,
      updateItem,
      removeItem,
      clear,
      applyPromo,
      // Aliases
      addItem,
      add,
      addLineItem,
      clearCart
    }),
    [
      cart,
      loading,
      error,
      refreshCart,
      addToCart,
      updateItem,
      removeItem,
      clear,
      applyPromo,
      addItem,
      add,
      addLineItem,
      clearCart
    ]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}

export default CartContext;
