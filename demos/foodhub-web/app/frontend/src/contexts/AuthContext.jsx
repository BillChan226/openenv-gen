import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('fh_token'));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!localStorage.getItem('fh_token')) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const data = await api.me();
      const userValue = data?.user || data?.me || data?.profile || data?.data?.user || null;
      setUser(userValue);
    } catch {
      localStorage.removeItem('fh_token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const persistAuth = useCallback((data) => {
    // Backend may respond as { token }, { data: { token } }, { auth: { token } }, etc.
    const tokenValue =
      data?.token ||
      data?.accessToken ||
      data?.jwt ||
      data?.auth?.token ||
      data?.data?.token ||
      data?.data?.accessToken;

    const userValue = data?.user || data?.profile || data?.me || data?.data?.user || data?.data?.me;

    if (tokenValue) {
      localStorage.setItem('fh_token', tokenValue);
      setToken(tokenValue);
    }
    if (userValue) setUser(userValue);

    return { token: tokenValue, user: userValue };
  }, []);

  const login = useCallback(
    async (payload) => {
      const data = await api.login(payload);
      persistAuth(data);
      return data;
    },
    [persistAuth]
  );

  const register = useCallback(
    async (payload) => {
      const data = await api.register(payload);
      persistAuth(data);
      return data;
    },
    [persistAuth]
  );

  const logout = useCallback(() => {
    localStorage.removeItem('fh_token');
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthed: !!token,
      login,
      register,
      logout,
      refreshMe
    }),
    [token, user, loading, login, register, logout, refreshMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export default AuthContext;
