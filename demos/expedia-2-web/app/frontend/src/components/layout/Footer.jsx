import React from 'react';
import Container from '../ui/Container';

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <Container className="py-10">
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <div className="text-sm font-black text-slate-900">Tripify</div>
            <p className="mt-2 text-sm text-slate-600">
              Expedia-style travel search demo. Compare prices for flights, stays, cars, and bundles.
            </p>
          </div>
          <div className="text-sm">
            <div className="font-bold text-slate-900">Company</div>
            <ul className="mt-2 space-y-2 text-slate-600">
              <li>About</li>
              <li>Careers</li>
              <li>Help</li>
            </ul>
          </div>
          <div className="text-sm">
            <div className="font-bold text-slate-900">Legal</div>
            <ul className="mt-2 space-y-2 text-slate-600">
              <li>Privacy</li>
              <li>Terms</li>
              <li>Cookie policy</li>
            </ul>
          </div>
        </div>
        <div className="mt-8 text-xs text-slate-500">© {new Date().getFullYear()} Tripify. All rights reserved.</div>
      </Container>
    </footer>
  );
}

export default Footer;
