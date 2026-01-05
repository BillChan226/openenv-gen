import React from 'react';
import { login as apiLogin, logout as apiLogout, me as apiMe, register as apiRegister } from '../services/auth';
import { getAccessToken } from '../services/auth';

const AuthCtx = React.createContext(null);

export function useAuth() {
  const ctx = React.useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export default function AuthProvider({ children }) {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  const refresh = React.useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const item = await apiMe();
      setUser(item?.user ?? null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const login = React.useCallback(async (payload) => {
    const item = await apiLogin(payload);
    setUser(item?.user ?? null);
    return item;
  }, []);

  const register = React.useCallback(async (payload) => {
    const item = await apiRegister(payload);
    setUser(item?.user ?? null);
    return item;
  }, []);

  const logout = React.useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({ user, loading, refresh, login, register, logout, isAuthed: !!user }),
    [user, loading, refresh, login, register, logout]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
