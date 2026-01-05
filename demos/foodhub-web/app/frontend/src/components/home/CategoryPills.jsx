import React from 'react';
import { UtensilsCrossed, ShoppingBasket, Store, Coffee, Pizza, Salad, IceCream, Sparkles } from 'lucide-react';

import Chip from '../ui/Chip.jsx';

const CATEGORIES = [
  { key: 'restaurants', label: 'Restaurants', icon: UtensilsCrossed },
  { key: 'grocery', label: 'Grocery', icon: ShoppingBasket, href: '/grocery' },
  { key: 'convenience', label: 'Convenience', icon: Store, href: '/goods' },
  { key: 'coffee', label: 'Coffee', icon: Coffee, href: '/goods' },
  { key: 'pizza', label: 'Pizza', icon: Pizza, href: '/goods' },
  { key: 'healthy', label: 'Healthy', icon: Salad, href: '/goods' },
  { key: 'dessert', label: 'Dessert', icon: IceCream, href: '/goods' },
  { key: 'offers', label: 'Offers', icon: Sparkles, href: '/goods' }
];

export function CategoryPills({ onSelect, selectedKey }) {
  return (
    <section className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-extrabold tracking-tight text-zinc-900">Browse categories</h2>
        <div className="text-xs text-zinc-500">Tap to explore</div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => {
          const Icon = c.icon;
          const active = selectedKey ? selectedKey === c.key : c.key === 'restaurants';
          return (
            <Chip
              key={c.key}
              as={c.href ? 'a' : 'button'}
              href={c.href}
              onClick={(e) => {
                if (!onSelect) return;
                e.preventDefault();
                onSelect(c.key);
              }}
              className={
                active
                  ? 'bg-[#FF3008]/10 text-[#FF3008] ring-1 ring-[#FF3008]/20'
                  : 'bg-zinc-50 text-zinc-700 hover:bg-zinc-100 ring-1 ring-zinc-200'
              }
            >
              <span className="inline-flex items-center gap-2">
                <Icon className="h-4 w-4" />
                <span className="font-semibold">{c.label}</span>
              </span>
            </Chip>
          );
        })}
      </div>
    </section>
  );
}

export default CategoryPills;
