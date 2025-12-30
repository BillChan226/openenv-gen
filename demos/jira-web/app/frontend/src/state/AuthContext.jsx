import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  getAuthToken,
  getMe,
  login as apiLogin,
  logout as apiLogout,
  setAuthToken,
} from '../services/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    // If we don't have a token, treat as logged out without calling /auth/me.
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return () => {
        mounted = false;
      };
    }

    getMe()
      .then((me) => {
        if (!mounted) return;
        // backend may return {user} or user directly
        setUser(me?.user || me || null);
      })
      .catch((err) => {
        if (!mounted) return;
        // 401 is a normal unauthenticated state (e.g. expired token). Avoid noisy console errors.
        if (err?.status !== 401) {
          console.warn('Failed to load session', err);
        }
        setUser(null);
        setAuthToken(null);
      })
      .finally(() => {
        if (!mounted) return;
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    setUser(data?.user || null);
    return data;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      logout,
      setUser,
    }),
    [user, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
