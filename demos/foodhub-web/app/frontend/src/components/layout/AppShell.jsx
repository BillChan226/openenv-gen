import React, { useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

import LeftSidebar from './LeftSidebar.jsx';
import TopHeader from './TopHeader.jsx';
import CartDrawer from '../cart/CartDrawer.jsx';

import { useCart } from '../../contexts/CartContext.jsx';

export function AppShell() {
  const [cartOpen, setCartOpen] = useState(false);
  const { cart, error } = useCart();
  const navigate = useNavigate();
  const location = useLocation();

  const cartCount = useMemo(() => {
    const items = cart?.items || [];
    return items.reduce((sum, it) => sum + (it.quantity || 0), 0);
  }, [cart]);

  React.useEffect(() => {
    if (error?.code === 'CART_RESTAURANT_MISMATCH') {
      toast.error('Your cart has items from another store. Please clear it to continue.');
    }
  }, [error]);

  const activePath = location.pathname;

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <div className="mx-auto max-w-[1400px] px-3 sm:px-4 lg:px-6">
        <div className="flex gap-4 lg:gap-6 py-3 lg:py-4">
          <LeftSidebar activePath={activePath} />

          <div className="min-w-0 flex-1">
            <TopHeader
              cartCount={cartCount}
              onCartClick={() => setCartOpen(true)}
              onLogoClick={() => navigate('/')}
            />

            <main className="mt-3 lg:mt-4">
              <Outlet />
            </main>
          </div>
        </div>
      </div>

      <CartDrawer open={cartOpen} onClose={() => setCartOpen(false)} />
    </div>
  );
}

export default AppShell;
