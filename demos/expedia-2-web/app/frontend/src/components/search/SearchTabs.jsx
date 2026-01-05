import React, { useMemo, useState } from 'react';
import clsx from 'clsx';
import Card from '../ui/Card';
import StaysSearchForm from './StaysSearchForm';
import FlightsSearchForm from './FlightsSearchForm';
import CarsSearchForm from './CarsSearchForm';
import PackagesSearchForm from './PackagesSearchForm';

const TABS = [
  { key: 'stays', label: 'Stays' },
  { key: 'flights', label: 'Flights' },
  { key: 'cars', label: 'Cars' },
  { key: 'packages', label: 'Packages' }
];

export function SearchTabs({ initialTab = 'stays' }) {
  const safeInitial = useMemo(() => (TABS.some((t) => t.key === initialTab) ? initialTab : 'stays'), [initialTab]);
  const [tab, setTab] = useState(safeInitial);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 p-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              'rounded-lg px-4 py-2 text-sm font-bold transition-colors',
              tab === t.key ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:bg-white/70'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-4 sm:p-6">
        {tab === 'stays' ? <StaysSearchForm /> : null}
        {tab === 'flights' ? <FlightsSearchForm /> : null}
        {tab === 'cars' ? <CarsSearchForm /> : null}
        {tab === 'packages' ? <PackagesSearchForm /> : null}
      </div>
    </Card>
  );
}

export default SearchTabs;
