import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext(null);

const THEME_KEY = 'jira_theme';

function applyThemeClass(theme) {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY);
    const initial = saved === 'light' || saved === 'dark' ? saved : 'dark';
    setTheme(initial);
    applyThemeClass(initial);
  }, []);

  const setAndPersist = useCallback((next) => {
    setTheme(next);
    localStorage.setItem(THEME_KEY, next);
    applyThemeClass(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setAndPersist(theme === 'dark' ? 'light' : 'dark');
  }, [setAndPersist, theme]);

  const value = useMemo(
    () => ({
      theme,
      setTheme: setAndPersist,
      toggleTheme,
    }),
    [theme, setAndPersist, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
