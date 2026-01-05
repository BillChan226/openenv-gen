import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Search, ShoppingBag, User } from 'lucide-react';

import Button from '../ui/Button.jsx';
import SearchBar from './SearchBar.jsx';

function HeaderPill({ to, label, active }) {
  return (
    <Link
      to={to}
      className={
        active
          ? 'rounded-full bg-white px-4 py-2 text-sm font-semibold text-zinc-900 shadow-sm ring-1 ring-zinc-200'
          : 'rounded-full px-4 py-2 text-sm font-semibold text-zinc-600 hover:text-zinc-900 hover:bg-white/70 transition-colors'
      }
    >
      {label}
    </Link>
  );
}

export function TopHeader({ cartCount = 0, onCartClick, onLogoClick }) {
  const location = useLocation();
  const navigate = useNavigate();

  const active = location.pathname;

  return (
    <div className="sticky top-0 z-30">
      <div className="rounded-2xl bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70 shadow-sm ring-1 ring-zinc-200">
        <div className="flex flex-col gap-3 p-3 sm:p-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onLogoClick}
              className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-zinc-100 transition-colors"
              aria-label="Go to home"
            >
              <div className="h-9 w-9 rounded-xl bg-[#FF3008] text-white flex items-center justify-center font-black tracking-tight shadow-sm">
                D
              </div>
              <div className="leading-tight">
                <div className="text-sm font-extrabold tracking-tight">DoorDash</div>
                <div className="text-xs text-zinc-500">Delivery & pickup</div>
              </div>
            </button>

            <div className="hidden lg:block flex-1">
              <SearchBar
                placeholder="Search stores and items"
                onSubmit={(q) => navigate(q ? `/goods?q=${encodeURIComponent(q)}` : '/goods')}
              />
            </div>

            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="ghost"
                className="hidden sm:inline-flex"
                onClick={() => navigate('/account')}
                leftIcon={<User className="h-4 w-4" />}
              >
                Account
              </Button>

              <Button
                onClick={onCartClick}
                className="relative"
                leftIcon={<ShoppingBag className="h-4 w-4" />}
              >
                Cart
                {cartCount > 0 ? (
                  <span className="ml-2 inline-flex min-w-6 items-center justify-center rounded-full bg-white/20 px-2 py-0.5 text-xs font-extrabold">
                    {cartCount}
                  </span>
                ) : null}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="lg:hidden flex-1">
              <SearchBar
                placeholder="Search stores and items"
                icon={<Search className="h-4 w-4" />}
                onSubmit={(q) => navigate(q ? `/goods?q=${encodeURIComponent(q)}` : '/goods')}
              />
            </div>

            <div className="hidden lg:flex items-center gap-2">
              <HeaderPill to="/" label="Restaurants" active={active === '/'} />
              <HeaderPill to="/grocery" label="Grocery" active={active.startsWith('/grocery')} />
              <HeaderPill to="/retail" label="Retail" active={active.startsWith('/retail')} />
              <HeaderPill to="/goods" label="Goods" active={active.startsWith('/goods')} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TopHeader;
