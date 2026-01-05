import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getMe, login as apiLogin, register as apiRegister } from '../services/api';
import { getCart as apiGetCart } from '../services/api';
import { setAuthToken } from '../services/apiClient';

const TOKEN_KEY = 'auth_token';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  const refresh = useCallback(async () => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const me = await getMe();
      setUser(me);
    } catch (e) {
      // token invalid
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async ({ email, password }) => {
    const res = await apiLogin({ email, password });
    const nextToken = res.token || res?.data?.token;
    const nextUser = res.user || res?.data?.user;
    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken);
      setToken(nextToken);
      if (nextUser) setUser(nextUser);
      else await refresh();

      // spec: fetch cart on login
      try {
        await apiGetCart();
      } catch {
        // ignore cart fetch errors
      }
    }
    return res;
  }, [refresh]);

  const register = useCallback(async ({ email, password, full_name }) => {
    const res = await apiRegister({ email, password, full_name });
    const nextToken = res.token || res?.data?.token;
    const nextUser = res.user || res?.data?.user;
    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken);
      setToken(nextToken);
      if (nextUser) setUser(nextUser);
      else await refresh();
    }
    return res;
  }, [refresh]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, loading, isAuthed: Boolean(token), login, register, logout, refresh }),
    [token, user, loading, login, register, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export default AuthContext;
