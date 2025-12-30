import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutGrid, Settings, LogOut, Search, Moon, Sun } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '../state/AuthContext.jsx';
import { useTheme } from '../state/ThemeContext.jsx';
import { useToast } from '../state/ToastContext.jsx';
import { search as apiSearch } from '../services/api.js';
import { Avatar } from '../shared/ui/Avatar.jsx';

function SidebarLink({ to, icon: Icon, label, testid }) {
  return (
    <NavLink
      to={to}
      data-testid={testid}
      className={({ isActive }) =>
        'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition ' +
        (isActive ? 'bg-bg-muted text-fg' : 'text-fg-muted hover:bg-bg-muted hover:text-fg')
      }
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();
  const navigate = useNavigate();

  const [q, setQ] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [results, setResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const debouncedQ = useMemo(() => q.trim(), [q]);

  useEffect(() => {
    if (!searchOpen) return;
    if (!debouncedQ) {
      setResults([]);
      return;
    }

    const ctrl = new AbortController();
    setSearchLoading(true);
    apiSearch({ q: debouncedQ })
      .then((data) => {
        const issues = data?.results?.issues || data?.issues || [];
        setResults(issues.slice(0, 8));
      })
      .catch(() => setResults([]))
      .finally(() => setSearchLoading(false));

    return () => ctrl.abort();
  }, [debouncedQ, searchOpen]);

  async function onLogout() {
    await logout();
    toast.push({ title: 'Logged out', variant: 'success' });
    navigate('/login');
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-border bg-bg-muted/30 hidden md:flex flex-col p-3">
        <div className="px-2 py-2 text-sm font-semibold">Jira Clone</div>
        <div className="mt-2 flex flex-col gap-1">
          <SidebarLink to="/dashboard" icon={LayoutGrid} label="Projects" testid="nav-dashboard" />
          <SidebarLink to="/settings" icon={Settings} label="Settings" testid="nav-settings" />
        </div>
        <div className="mt-auto pt-3 border-t border-border">
          <button
            type="button"
            className="btn w-full justify-start"
            onClick={onLogout}
            data-testid="logout"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Logout
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur">
          <div className="h-14 px-4 flex items-center gap-3">
            <div className="md:hidden font-semibold">Jira Clone</div>

            <div className="flex-1" />

            <div className="relative w-[min(520px,60vw)] hidden sm:block">
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
                <input
                  className="input pl-9"
                  placeholder="Search issues…"
                  value={q}
                  onFocus={() => setSearchOpen(true)}
                  onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
                  onChange={(e) => setQ(e.target.value)}
                  data-testid="global-search"
                />
              </div>

              {searchOpen && (results.length > 0 || searchLoading) && (
                <div className="absolute mt-2 w-full surface overflow-hidden">
                  <div className="px-3 py-2 text-xs text-fg-muted border-b border-border">
                    {searchLoading ? 'Searching…' : 'Issues'}
                  </div>
                  <div className="max-h-80 overflow-auto">
                    {results.map((it) => (
                      <button
                        key={it.id}
                        type="button"
                        className="w-full text-left px-3 py-2 hover:bg-bg-muted flex items-center gap-2"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setSearchOpen(false);
                          setQ('');
                          navigate(`/projects/${it.projectKey || it.project_key}/board?issue=${it.id}`);
                        }}
                        data-testid={`search-result-${it.id}`}
                      >
                        <span className="chip">{it.key}</span>
                        <span className="text-sm truncate">{it.summary || it.title}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              className="btn btn-ghost h-9 w-9 p-0"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              data-testid="theme-toggle"
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>

            <div className="flex items-center gap-2">
              <Avatar src={user?.avatarUrl || user?.avatar_url} name={user?.name || user?.email} size={28} />
              <div className="hidden lg:block">
                <div className="text-sm font-medium leading-4">{user?.name || 'User'}</div>
                <div className="text-xs text-fg-muted">{user?.email}</div>
              </div>
            </div>
          </div>
        </header>

        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
