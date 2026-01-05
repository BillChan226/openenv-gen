import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, MapPin, Search } from 'lucide-react';

const HERO_IMAGE =
  'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=2400&q=60';

function TabButton({ active, children }) {
  return (
    <button
      type="button"
      className={
        active
          ? 'rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm'
          : 'rounded-full px-4 py-2 text-sm font-semibold text-white/90 hover:bg-white/15'
      }
    >
      {children}
    </button>
  );
}

function SearchCard() {
  return (
    <div className="mx-auto -mt-16 w-full max-w-5xl rounded-2xl bg-white p-4 shadow-[0_18px_40px_rgba(2,6,23,0.18)] ring-1 ring-slate-200 md:p-5">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
        <TabButton active>Stays</TabButton>
        <TabButton>Flights</TabButton>
        <TabButton>Cars</TabButton>
        <TabButton>Packages</TabButton>
        <div className="ml-auto hidden items-center gap-2 text-xs font-medium text-slate-600 md:flex">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2 py-1 ring-1 ring-slate-200">
            <MapPin className="h-3.5 w-3.5" />
            United States
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
          <label htmlFor="home-destination" className="mb-1 block text-xs font-semibold text-slate-700">
            Going to
          </label>
          <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 focus-within:ring-4 focus-within:ring-blue-100">
            <MapPin className="h-4 w-4 text-slate-500" aria-hidden="true" focusable="false" />
            <input
              id="home-destination"
              name="destination"
              className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              placeholder="Where to?"
              autoComplete="off"
            />
          </div>
        </div>

        <div className="md:col-span-3">
          <label htmlFor="home-checkin" className="mb-1 block text-xs font-semibold text-slate-700">
            Check-in
          </label>
          <input
            id="home-checkin"
            name="checkin"
            type="date"
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-4 focus:ring-blue-100"
          />
        </div>

        <div className="md:col-span-3">
          <label htmlFor="home-checkout" className="mb-1 block text-xs font-semibold text-slate-700">
            Check-out
          </label>
          <input
            id="home-checkout"
            name="checkout"
            type="date"
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-4 focus:ring-blue-100"
          />
        </div>

        <div className="md:col-span-2">
          <button
            type="button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#1668E3] px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#0f5ed6] focus:ring-4 focus:ring-blue-200"
          >
            <Search className="h-4 w-4" />
            Search
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <label htmlFor="home-add-flight" className="inline-flex items-center gap-2">
          <input id="home-add-flight" type="checkbox" className="h-4 w-4 rounded border-slate-300" />
          Add a flight
        </label>
        <label htmlFor="home-add-car" className="inline-flex items-center gap-2">
          <input id="home-add-car" type="checkbox" className="h-4 w-4 rounded border-slate-300" />
          Add a car
        </label>
      </div>
    </div>
  );
}

function PromoStrip() {
  const navigate = useNavigate();

  return (
    <div className="mx-auto mt-6 w-full max-w-5xl rounded-2xl bg-[#E7F1FF] px-4 py-3 text-sm text-slate-800 ring-1 ring-blue-100">
      <span className="font-semibold">Members save 10% or more</span> on select hotels.
      <button
        type="button"
        className="ml-2 font-semibold text-[#1668E3] hover:underline"
        onClick={() => navigate('/login')}
      >
        Sign in
      </button>
    </div>
  );
}

function DealCard({ title, subtitle, img }) {
  return (
    <div className="group overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div className="relative h-40 w-full overflow-hidden bg-slate-100">
        <img
          src={img}
          alt={title}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <button
          type="button"
          aria-label="Save"
          className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-slate-800 shadow-sm ring-1 ring-white/60 hover:bg-white"
        >
          <Heart className="h-4 w-4" />
        </button>
      </div>
      <div className="p-4">
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        <div className="mt-1 text-sm text-slate-600">{subtitle}</div>
      </div>
    </div>
  );
}

export default function Home({ initialTab = 'stays' }) {
  return (
    <div>
      {/* Hero image */}
      <section className="relative overflow-hidden rounded-3xl bg-[#0B1F3B]">
        <div className="absolute inset-0">
          <img
            src={HERO_IMAGE}
            alt="Scenic travel destination"
            className="h-full w-full object-cover opacity-85"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0B1F3B]/85 via-[#0B1F3B]/55 to-[#0B1F3B]/20" />
        </div>

        <div className="relative px-6 pb-24 pt-14 md:px-10 md:pb-28">
          <div className="max-w-3xl">
            <h1 className="font-serif text-4xl font-semibold tracking-tight text-white md:text-6xl">
              Where to?
            </h1>
            <p className="mt-3 max-w-xl text-base text-white/85">
              Search deals on hotels, homes, and much more.
            </p>
          </div>
        </div>
      </section>

      {/* Search card overlaps hero */}
      <SearchCard />

      <PromoStrip />

      {/* Deals */}
      <section className="mx-auto mt-10 w-full max-w-5xl">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Today’s top deals</h2>
            <p className="mt-1 text-sm text-slate-600">Save on stays, flights, and more.</p>
          </div>
          <button type="button" className="text-sm font-semibold text-[#1668E3] hover:underline">
            See all deals
          </button>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DealCard
            title="Beachfront escapes"
            subtitle="Up to 25% off select stays"
            img="https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1200&q=60"
          />
          <DealCard
            title="City weekend"
            subtitle="Member prices on top hotels"
            img="https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1200&q=60"
          />
          <DealCard
            title="Family-friendly"
            subtitle="Free cancellation on many rooms"
            img="https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=60"
          />
        </div>
      </section>
    </div>
  );
}
