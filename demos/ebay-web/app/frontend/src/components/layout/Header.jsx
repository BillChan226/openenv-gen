import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Search, ShoppingCart } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { EbayLogo } from './EbayLogo.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { useCart } from '../../contexts/CartContext.jsx';
import { CategoriesNav } from '../nav/CategoriesNav.jsx';

export function Header() {
  const { user, isSignedIn, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');

  useEffect(() => {
    // keep query local; no-op
  }, []);

  const welcomeText = useMemo(() => {
    if (!isSignedIn) return 'Welcome to eBay';
    const name = user?.name || user?.fullName || user?.firstName;
    return name ? `Welcome, ${name}!` : 'Welcome!';
  }, [isSignedIn, user]);

  function onSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    navigate(`/category/all?q=${encodeURIComponent(q)}`);
  }

  return (
    <header className="sticky top-0 z-40 bg-white shadow-header">
      <div className="border-b border-gray-200">
        <div className="container-page">
          <div className="flex items-center justify-end gap-4 py-2 text-[13px]">
            <span className="text-gray-600" data-testid="welcome-text">
              {welcomeText}
            </span>
            <Link className="hover:underline" to="/account" data-testid="nav-my-account">
              My Account
            </Link>
            <Link className="hover:underline" to="/account/wishlist" data-testid="nav-my-wishlist">
              My Wish List
            </Link>
            {isSignedIn ? (
              <button
                type="button"
                className="hover:underline"
                onClick={() => {
                  logout();
                  navigate('/');
                }}
                data-testid="nav-sign-out"
              >
                Sign Out
              </button>
            ) : (
              <Link className="hover:underline" to="/login" data-testid="nav-sign-in">
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="container-page">
        <div className="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between">
          <Link to="/" className="inline-flex items-center" data-testid="nav-home-logo">
            <EbayLogo />
          </Link>

          <div className="flex flex-1 items-start justify-end gap-4">
            <div className="w-full max-w-xl">
              <form onSubmit={onSubmit} className="relative" data-testid="header-search-form">
                <input
                  className="h-9 w-full rounded border border-gray-300 px-3 pr-9 text-sm placeholder:text-gray-400 focus-ring"
                  placeholder="Search entire store here…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  data-testid="header-search-input"
                />
                <button
                  type="submit"
                  className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 text-gray-500 hover:text-gray-700 focus-ring"
                  aria-label="Search"
                  data-testid="header-search-submit"
                >
                  <Search className="h-4 w-4" aria-hidden="true" />
                </button>
              </form>
              <div className="mt-1 text-[13px]">
                <NavLink to="/advanced-search" className="hover:underline" data-testid="nav-advanced-search">
                  Advanced Search
                </NavLink>
              </div>
            </div>

            <Link to="/cart" className="relative mt-1 inline-flex items-center" data-testid="nav-cart">
              <ShoppingCart className="h-6 w-6 text-gray-600" aria-hidden="true" />
              {itemCount > 0 ? (
                <span
                  className="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-blue px-1 text-[11px] font-bold text-white"
                  data-testid="cart-badge"
                >
                  {itemCount}
                </span>
              ) : null}
              <span className="sr-only">Cart</span>
            </Link>
          </div>
        </div>
      </div>

      <div className="bg-gray-100">
        <div className="container-page">
          <CategoriesNav />
        </div>
      </div>
    </header>
  );
}
