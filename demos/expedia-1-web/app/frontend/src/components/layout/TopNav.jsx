import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Menu, Search, ShoppingCart, User } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import clsx from 'clsx';
import { useAuth } from '../../context/AuthContext';

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15">
        <span className="text-lg font-extrabold tracking-tight text-white">e</span>
      </div>
      <div className="leading-tight">
        <div className="text-base font-extrabold tracking-tight text-white">Expedia</div>
        <div className="text-xs text-white/75">Voyager</div>
      </div>
    </Link>
  );
}

function NavPill({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'rounded-full px-3 py-1.5 text-sm font-semibold transition-colors',
          isActive ? 'bg-white text-brand-700' : 'text-white/90 hover:bg-white/10'
        )
      }
    >
      {children}
    </NavLink>
  );
}

export default function TopNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-brand-800/40 bg-gradient-to-r from-brand-800 via-brand-700 to-brand-800">
      <div className="container-app">
        <div className="flex h-16 items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              className="inline-flex items-center justify-center rounded-xl p-2 text-white/90 hover:bg-white/10 focus:ring-4 focus:ring-white/15 md:hidden"
              aria-label="Open menu"
              type="button"
            >
              <Menu className="h-5 w-5" />
            </button>
            <Brand />
            <nav className="hidden items-center gap-1 md:flex">
              <NavPill to="/stays">Stays</NavPill>
              <NavPill to="/flights">Flights</NavPill>
              <NavPill to="/cars">Cars</NavPill>
              <NavPill to="/packages">Packages</NavPill>
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/search"
              className="hidden items-center gap-2 rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white/90 ring-1 ring-white/10 hover:bg-white/15 focus:ring-4 focus:ring-white/15 sm:inline-flex"
            >
              <Search className="h-4 w-4" />
              Search
            </Link>

            <Link
              to="/cart"
              className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white/90 ring-1 ring-white/10 hover:bg-white/15 focus:ring-4 focus:ring-white/15"
            >
              <ShoppingCart className="h-4 w-4" />
              <span className="hidden sm:inline">Cart</span>
            </Link>

            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-white/40 hover:bg-white/95 focus:ring-4 focus:ring-white/30"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-700 text-white">
                    <User className="h-4 w-4" />
                  </span>
                  <span className="hidden sm:inline">{user?.name || user?.email || 'Account'}</span>
                </button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="end"
                  sideOffset={10}
                  className="z-50 w-56 rounded-2xl bg-white p-2 shadow-dropdown ring-1 ring-slate-200"
                >
                  {user ? (
                    <>
                      <DropdownMenu.Item
                        className="cursor-pointer rounded-xl px-3 py-2 text-sm text-slate-800 outline-none hover:bg-slate-50"
                        onSelect={() => navigate('/account')}
                      >
                        Profile
                      </DropdownMenu.Item>
                      <DropdownMenu.Item
                        className="cursor-pointer rounded-xl px-3 py-2 text-sm text-slate-800 outline-none hover:bg-slate-50"
                        onSelect={() => navigate('/trips')}
                      >
                        Trips
                      </DropdownMenu.Item>
                      <DropdownMenu.Separator className="my-2 h-px bg-slate-100" />
                      <DropdownMenu.Item
                        className="cursor-pointer rounded-xl px-3 py-2 text-sm text-red-700 outline-none hover:bg-red-50"
                        onSelect={() => logout()}
                      >
                        Sign out
                      </DropdownMenu.Item>
                    </>
                  ) : (
                    <>
                      <DropdownMenu.Item
                        className="cursor-pointer rounded-xl px-3 py-2 text-sm text-slate-800 outline-none hover:bg-slate-50"
                        onSelect={() => navigate('/login')}
                      >
                        Sign in
                      </DropdownMenu.Item>
                      <DropdownMenu.Item
                        className="cursor-pointer rounded-xl px-3 py-2 text-sm text-slate-800 outline-none hover:bg-slate-50"
                        onSelect={() => navigate('/register')}
                      >
                        Create account
                      </DropdownMenu.Item>
                    </>
                  )}
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          </div>
        </div>
      </div>
    </header>
  );
}
