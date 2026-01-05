import React from 'react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="container-app py-10">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <div className="text-sm font-extrabold tracking-tight text-slate-900">Expedia Voyager</div>
            <p className="mt-2 text-sm text-slate-600">
              A demo travel booking experience inspired by Expedia. Search flights, stays, cars and packages.
            </p>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Explore</div>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li>Stays</li>
              <li>Flights</li>
              <li>Cars</li>
              <li>Packages</li>
            </ul>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Support</div>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li>Help center</li>
              <li>Cancellation options</li>
              <li>Travel alerts</li>
            </ul>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Legal</div>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li>Terms</li>
              <li>Privacy</li>
              <li>Cookies</li>
            </ul>
          </div>
        </div>
        <div className="mt-10 flex flex-col gap-2 border-t border-slate-100 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <div>© {new Date().getFullYear()} Expedia Voyager</div>
          <div>Built for demo purposes. Not affiliated with Expedia Group.</div>
        </div>
      </div>
    </footer>
  );
}
