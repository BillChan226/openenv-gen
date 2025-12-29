import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getWishlist, removeWishlistItem, toggleWishlist } from '../services/api.js';
import { useAuth } from './AuthContext.jsx';

const WishlistContext = createContext(null);
const LS_KEY = 'wishlist_snapshot_v1';

function safeParse(json) {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function WishlistProvider({ children }) {
  const { isSignedIn } = useAuth();
  const [wishlist, setWishlist] = useState(() => safeParse(localStorage.getItem(LS_KEY)) || { items: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const persist = useCallback((next) => {
    setWishlist(next);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
  }, []);

  const refresh = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWishlist();
      persist(data);
    } catch (e) {
      setError(e.message || 'Failed to load wish list');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, persist]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isInWishlist = useCallback(
    (productId) => {
      return wishlist.items?.some((i) => i.productId === productId || i.id === productId || i.product?.id === productId);
    },
    [wishlist.items]
  );

  const toggle = useCallback(
    async (product) => {
      const productId = product?.id || product;
      const exists = isInWishlist(productId);
      const nextItems = exists
        ? wishlist.items.filter((i) => (i.productId || i.id || i.product?.id) !== productId)
        : [...(wishlist.items || []), { productId, product }];
      persist({ ...wishlist, items: nextItems });

      if (!isSignedIn) return;
      try {
        const updated = await toggleWishlist(productId);
        persist(updated);
      } catch (e) {
        setError(e.message || 'Failed to update wish list');
        refresh();
      }
    },
    [isSignedIn, isInWishlist, persist, refresh, wishlist]
  );

  const remove = useCallback(
    async (productId) => {
      const nextItems = wishlist.items.filter((i) => (i.productId || i.id || i.product?.id) !== productId);
      persist({ ...wishlist, items: nextItems });

      if (!isSignedIn) return;
      try {
        const updated = await removeWishlistItem(productId);
        persist(updated);
      } catch (e) {
        setError(e.message || 'Failed to remove item');
        refresh();
      }
    },
    [isSignedIn, persist, refresh, wishlist]
  );

  const value = useMemo(
    () => ({ wishlist, loading, error, refresh, toggle, remove, isInWishlist, clearError: () => setError(null) }),
    [wishlist, loading, error, refresh, toggle, remove, isInWishlist]
  );

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}

export function useWishlist() {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error('useWishlist must be used within WishlistProvider');
  return ctx;
}
