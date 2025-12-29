import { Link } from 'react-router-dom';
import { useState } from 'react';

export function Footer() {
  const [email, setEmail] = useState('');

  function onSubmit(e) {
    e.preventDefault();
    setEmail('');
    // demo only
  }

  return (
    <footer className="mt-10 border-t border-gray-200 bg-white">
      <div className="container-page py-8">
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Customer Service</h4>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link className="link-muted" to="#" data-testid="footer-privacy">
                  Privacy and Cookie Policy
                </Link>
              </li>
              <li>
                <Link className="link-muted" to="#" data-testid="footer-search-terms">
                  Search Terms
                </Link>
              </li>
              <li>
                <Link className="link-muted" to="/advanced-search" data-testid="footer-advanced-search">
                  Advanced Search
                </Link>
              </li>
              <li>
                <Link className="link-muted" to="#" data-testid="footer-orders-returns">
                  Orders and Returns
                </Link>
              </li>
              <li>
                <Link className="link-muted" to="#" data-testid="footer-contact">
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900">About</h4>
            <p className="mt-3 text-sm text-gray-600">
              Demo storefront for browsing, searching, and managing a cart and wish list.
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900">Newsletter</h4>
            <p className="mt-3 text-sm text-gray-600">Get product updates and deals (demo only).</p>
            <form className="mt-3 flex gap-2" onSubmit={onSubmit} data-testid="newsletter-form">
              <input
                className="h-9 flex-1 rounded border border-gray-300 px-3 text-sm placeholder:text-gray-400 focus-ring"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="newsletter-email"
              />
              <button
                type="submit"
                className="h-9 rounded bg-brand-blue px-4 text-sm font-semibold text-white hover:opacity-95 focus-ring"
                data-testid="newsletter-submit"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>

        <div className="mt-8 text-xs text-gray-500">© {new Date().getFullYear()} eBay Web Demo</div>
      </div>
    </footer>
  );
}
