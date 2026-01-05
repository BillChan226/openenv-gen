import React from 'react';
import { Map as MapIcon } from 'lucide-react';
import Card from '../ui/Card';

// Placeholder fallback per spec: Leaflet/OSM can be integrated, but keep safe fallback.
export function MapPanel({ title = 'Map', subtitle = 'Map preview', heightClass = 'h-[420px]' }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 bg-white p-4">
        <div className="text-sm font-black text-slate-900">{title}</div>
        <div className="text-xs text-slate-500">{subtitle}</div>
      </div>
      <div className={['grid place-items-center bg-gradient-to-br from-slate-50 to-slate-100', heightClass].join(' ')}>
        <div className="text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
            <MapIcon className="h-6 w-6 text-brand-600" />
          </div>
          <div className="mt-3 text-sm font-bold text-slate-900">Map coming soon</div>
          <div className="mt-1 text-xs text-slate-500">Leaflet + OpenStreetMap placeholder</div>
        </div>
      </div>
    </Card>
  );
}

export default MapPanel;
