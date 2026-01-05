import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Heart, Luggage, UserCircle } from 'lucide-react';
import Container from '../ui/Container';
import Button from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';

function TopLink({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          'text-sm font-semibold transition-colors',
          isActive ? 'text-white' : 'text-white/85 hover:text-white'
        ].join(' ')
      }
    >
      {children}
    </NavLink>
  );
}

export function Header() {
  const { user, isAuthed, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="bg-gradient-to-r from-brand-700 via-brand-600 to-brand-700 text-white">
      <Container className="py-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/15 ring-1 ring-white/20">
              <span className="text-lg font-black">T</span>
            </div>
            <div className="leading-tight">
              <div className="text-sm font-black tracking-wide">Tripify</div>
              <div className="text-xs text-white/80">Search • Book • Go</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 md:flex">
            <TopLink to="/hotels">Stays</TopLink>
            <TopLink to="/flights">Flights</TopLink>
            <TopLink to="/cars">Cars</TopLink>
            <TopLink to="/packages">Packages</TopLink>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/favorites"
              className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white/90 hover:bg-white/10"
            >
              <Heart className="h-4 w-4" />
              <span className="hidden sm:inline">Favorites</span>
            </Link>
            <Link
              to="/trips"
              className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white/90 hover:bg-white/10"
            >
              <Luggage className="h-4 w-4" />
              <span className="hidden sm:inline">Trips</span>
            </Link>
            <Link
              to="/cart"
              className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white/90 hover:bg-white/10"
            >
              <span className="hidden sm:inline">Cart</span>
            </Link>

            <div className="hidden h-8 w-px bg-white/20 sm:block" />

            {isAuthed ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/profile')}
                  className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white/90 hover:bg-white/10"
                >
                  <UserCircle className="h-5 w-5" />
                  <span className="hidden sm:inline">{user?.full_name || user?.email || 'Account'}</span>
                </button>
                <Button variant="secondary" size="sm" onClick={logout}>
                  Sign out
                </Button>
              </div>
            ) : (
              <Button variant="secondary" size="sm" onClick={() => navigate('/login')}>
                Sign in
              </Button>
            )}
          </div>
        </div>
      </Container>
    </header>
  );
}

export default Header;
