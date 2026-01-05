import React from 'react';
import { NavLink } from 'react-router-dom';
import { Heart, Home, Plus, Receipt, ShoppingBag, Store, User } from 'lucide-react';
import clsx from 'clsx';

const nav = [
  { key: 'home', label: 'Home', icon: Home, to: '/' },
  { key: 'grocery', label: 'Grocery', icon: ShoppingBag, to: '/grocery' },
  { key: 'retail', label: 'Retail', icon: Store, to: '/retail' },
  { key: 'pharmacy', label: 'Pharmacy', icon: Plus, to: '/pharmacy' },
  { key: 'orders', label: 'Orders', icon: Receipt, to: '/orders' },
  { key: 'favorites', label: 'Favorites', icon: Heart, to: '/favorites' },
  { key: 'profile', label: 'Profile', icon: User, to: '/profile' }
];

export default function LeftSidebar() {
  return (
    <aside className="hidden lg:flex lg:w-72 lg:flex-col lg:gap-6 lg:border-r lg:border-neutral-200 lg:bg-white lg:px-5 lg:py-6">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-brand-500 text-white shadow-soft">
          <span className="text-lg font-extrabold">F</span>
        </div>
        <div>
          <div className="text-sm font-extrabold tracking-tight text-neutral-900">FoodHub</div>
          <div className="text-xs font-semibold text-neutral-500">Delivery • Pickup</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.key}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition-colors',
                  isActive
                    ? 'bg-brand-500 text-white shadow-soft'
                    : 'text-neutral-800 hover:bg-neutral-100'
                )
              }
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto rounded-2xl bg-neutral-50 p-4">
        <div className="text-sm font-extrabold text-neutral-900">Tip</div>
        <div className="mt-1 text-xs font-medium leading-relaxed text-neutral-600">
          Browse restaurants, add items to your cart, then checkout. This is a demo UI.
        </div>
      </div>
    </aside>
  );
}
