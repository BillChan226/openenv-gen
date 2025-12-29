import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { addCartItem, getCart, removeCartItem, updateCartItem } from '../services/api.js';
import { useAuth } from './AuthContext.jsx';

const CartContext = createContext(null);
const LS_KEY = 'cart_snapshot_v1';

function safeParse(json) {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function CartProvider({ children }) {
  const { isSignedIn } = useAuth();
  const [cart, setCart] = useState(() => safeParse(localStorage.getItem(LS_KEY)) || { items: [], subtotal: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const persist = useCallback((next) => {
    setCart(next);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
  }, []);

  const refresh = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCart();
      persist(data);
    } catch (e) {
      setError(e.message || 'Failed to load cart');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, persist]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addItem = useCallback(
    async (product, quantity = 1) => {
      // optimistic
      const existing = cart.items.find((i) => i.productId === product.id);
      const nextItems = existing
        ? cart.items.map((i) => (i.productId === product.id ? { ...i, quantity: i.quantity + quantity } : i))
        : [...cart.items, { productId: product.id, product, quantity }];
      persist({ ...cart, items: nextItems });

      if (!isSignedIn) return;
      try {
        const updated = await addCartItem(product.id, quantity);
        persist(updated);
      } catch (e) {
        setError(e.message || 'Failed to add item');
        refresh();
      }
    },
    [cart, isSignedIn, persist, refresh]
  );

  const setQuantity = useCallback(
    async (productId, quantity) => {
      const nextItems = cart.items
        .map((i) => (i.productId === productId ? { ...i, quantity } : i))
        .filter((i) => i.quantity > 0);
      persist({ ...cart, items: nextItems });

      if (!isSignedIn) return;
      try {
        const updated = await updateCartItem(productId, quantity);
        persist(updated);
      } catch (e) {
        setError(e.message || 'Failed to update quantity');
        refresh();
      }
    },
    [cart, isSignedIn, persist, refresh]
  );

  const removeItem = useCallback(
    async (productId) => {
      const nextItems = cart.items.filter((i) => i.productId !== productId);
      persist({ ...cart, items: nextItems });

      if (!isSignedIn) return;
      try {
        const updated = await removeCartItem(productId);
        persist(updated);
      } catch (e) {
        setError(e.message || 'Failed to remove item');
        refresh();
      }
    },
    [cart, isSignedIn, persist, refresh]
  );

  const itemCount = useMemo(() => cart.items.reduce((sum, i) => sum + (i.quantity || 0), 0), [cart.items]);

  const value = useMemo(
    () => ({ cart, itemCount, loading, error, refresh, addItem, setQuantity, removeItem, clearError: () => setError(null) }),
    [cart, itemCount, loading, error, refresh, addItem, setQuantity, removeItem]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}
