import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin } from 'lucide-react';

import RestaurantCard from '../components/restaurants/RestaurantCard.jsx';
import Button from '../components/ui/Button.jsx';
import * as CategoryPillsModule from '../components/home/CategoryPills.jsx';
import PromoBanners from '../components/home/PromoBanners.jsx';

import { listRestaurants } from '../services/api.js';

const CategoryPills = CategoryPillsModule?.default || CategoryPillsModule?.CategoryPills;

export function Home() {
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const data = await listRestaurants({ limit: 12, offset: 0 });
        const items = data?.items || data || [];
        if (mounted) setRestaurants(items);
      } catch (e) {
        if (mounted) setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const topPicks = useMemo(() => restaurants.slice(0, 8), [restaurants]);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-[#FF3008] to-[#FF3008]/80 text-white p-5 sm:p-6 lg:p-8 shadow-[0_20px_70px_rgba(255,48,8,0.25)]">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-white/80">DoorDash</div>
            <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight">
              Get anything delivered.
            </h1>
            <p className="mt-2 text-sm sm:text-base text-white/90 max-w-xl">
              Restaurants, groceries, and retail. Fast delivery, easy pickup.
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
                <MapPin className="h-4 w-4" />
                123 Main St
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
                Delivery · 25–35 min
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <Button asChild className="bg-white text-[#FF3008] hover:bg-white/90">
              <Link to="/grocery">Shop grocery</Link>
            </Button>
            <Button asChild variant="secondary" className="bg-white/15 text-white hover:bg-white/20 ring-1 ring-white/20">
              <Link to="/goods">Browse goods</Link>
            </Button>
          </div>
        </div>
      </div>

      <CategoryPills />
      <PromoBanners />

      <section>
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-lg font-extrabold tracking-tight text-zinc-900">Top picks near you</h2>
            <p className="mt-1 text-sm text-zinc-600">Popular restaurants based on your area</p>
          </div>
          <Link className="text-sm font-semibold text-[#FF3008] hover:underline" to="/goods">
            See all
          </Link>
        </div>

        <div className="mt-4">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div
                  key={idx}
                  className="h-[150px] rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 animate-pulse"
                />
              ))}
            </div>
          ) : error ? (
            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200 p-4">
              <div className="text-sm font-extrabold text-zinc-900">Could not load restaurants</div>
              <div className="mt-1 text-sm text-zinc-600">{error?.message || 'Please try again.'}</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {topPicks.map((r) => (
                <RestaurantCard key={r.id} restaurant={r} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default Home;
