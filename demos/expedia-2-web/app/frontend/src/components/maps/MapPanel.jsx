import React, { useMemo } from 'react';
import { MapContainer, Marker, TileLayer, Tooltip } from 'react-leaflet';
import L from 'leaflet';

// Fix default marker icons in Vite builds
import marker2x from 'leaflet/dist/images/marker-icon-2x.png';
import marker1x from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconRetinaUrl: marker2x,
  iconUrl: marker1x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

export default function MapPanel({ lat, lng, markers = [] }) {
  const center = useMemo(() => {
    const fallback = { lat: 37.7749, lng: -122.4194 };
    if (typeof lat === 'number' && typeof lng === 'number') return [lat, lng];
    if (markers?.length && typeof markers[0]?.lat === 'number' && typeof markers[0]?.lng === 'number') {
      return [markers[0].lat, markers[0].lng];
    }
    return [fallback.lat, fallback.lng];
  }, [lat, lng, markers]);

  const normalizedMarkers = useMemo(() => {
    return (markers || [])
      .filter((m) => typeof m?.lat === 'number' && typeof m?.lng === 'number')
      .slice(0, 50);
  }, [markers]);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">Map</div>
          <div className="text-xs text-slate-600">Explore the area</div>
        </div>
        <div className="text-xs text-slate-500">Powered by OpenStreetMap</div>
      </div>

      <div className="h-[420px] w-full">
        <MapContainer center={center} zoom={13} scrollWheelZoom className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {normalizedMarkers.map((m) => (
            <Marker key={m.id || `${m.lat}-${m.lng}`} position={[m.lat, m.lng]}>
              {m.label ? (
                <Tooltip direction="top" offset={[0, -20]} opacity={1}>
                  <div className="text-xs font-semibold">{m.label}</div>
                  {m.subLabel ? <div className="text-[11px] text-slate-600">{m.subLabel}</div> : null}
                </Tooltip>
              ) : null}
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
