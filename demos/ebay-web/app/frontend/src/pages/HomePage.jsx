import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { listProducts } from '../services/api.js';
import { Spinner } from '../components/ui/Spinner.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { EmptyState } from '../components/ui/EmptyState.jsx';
import { Button } from '../components/ui/Button.jsx';
import { useCart } from '../contexts/CartContext.jsx';
import { useWishlist } from '../contexts/WishlistContext.jsx';

function formatPrice(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value ?? '');
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(n);
}

function Stars({ value }) {
  const v = Math.max(0, Math.min(5, Number(value) || 0));
  const full = Math.round(v);
  return (
    <div className="flex items-center gap-0.5" aria-label={`Rating ${v} out of 5`}>
      {Array.from({ length: 5 }).map((_, idx) => {
        const filled = idx < full;
        return (
          <span key={idx} className={filled ? 'text-amber-500' : 'text-slate-300'} aria-hidden="true">
            ★
          </span>
        );
      })}
    </div>
  );
}

function resolveImageUrl(product) {
  return (
    product?.image ||
    product?.imageUrl ||
    product?.thumbnailUrl ||
    (Array.isArray(product?.images) ? product.images[0] : null) ||
    null
  );
}

function ProductCard({ product, onAddToCart, onToggleWishlist, inWishlist }) {
  const [adding, setAdding] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [actionError, setActionError] = useState('');

  const imageUrl = resolveImageUrl(product);
  const rating = Number(product?.rating ?? product?.avgRating ?? 0) || 0;
  const reviewCount = Number(product?.reviewCount ?? product?.reviewsCount ?? 0) || 0;

  async function handleAdd() {
    setActionError('');
    setAdding(true);
    try {
      await onAddToCart?.(product);
    } catch (e) {
      setActionError(e?.message || 'Failed to add to cart');
    } finally {
      setAdding(false);
    }
  }

  async function handleToggleWishlist() {
    setActionError('');
    setToggling(true);
    try {
      await onToggleWishlist?.(product);
    } catch (e) {
      setActionError(e?.message || 'Failed to update wishlist');
    } finally {
      setToggling(false);
    }
  }

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex gap-4">
        <div className="h-24 w-24 shrink-0 overflow-hidden rounded-md bg-slate-100">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={product?.name ? `${product.name} image` : 'Product image'}
              className="h-full w-full object-cover"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-xs text-slate-500">No image</div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-900">{product?.name}</div>
              <div className="mt-1 text-xs text-slate-500">SKU: {product?.sku || '—'}</div>
            </div>
            <div className="text-sm font-semibold text-slate-900">{formatPrice(product?.price)}</div>
          </div>

          <div className="mt-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Stars value={rating} />
              <div className="text-xs text-slate-600">
                <span className="font-medium">{rating ? rating.toFixed(1) : '—'}</span>
                <span className="text-slate-500"> ({reviewCount})</span>
              </div>
            </div>

            <button
              type="button"
              className={
                inWishlist
                  ? 'rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700'
                  : 'rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700'
              }
              onClick={handleToggleWishlist}
              disabled={toggling}
              aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
              data-testid={`product-card-wishlist-${product?.id ?? product?.sku}`}
            >
              {toggling ? '…' : inWishlist ? '♥ Saved' : '♡ Save'}
            </button>
          </div>

          {product?.shortDescription ? (
            <p className="mt-3 line-clamp-2 text-sm text-slate-700">{product.shortDescription}</p>
          ) : null}

          {actionError ? (
            <div className="mt-2 text-xs text-rose-700" role="alert" data-testid={`product-card-error-${product?.id ?? product?.sku}`}>
              {actionError}
            </div>
          ) : null}

          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="text-xs text-slate-500">{product?.categorySlug ? `Category: ${product.categorySlug}` : ''}</div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={handleAdd}
                disabled={adding}
                data-testid={`product-card-add-${product?.id ?? product?.sku}`}
              >
                {adding ? 'Adding…' : 'Add to cart'}
              </Button>
              {product?.categorySlug ? (
                <Link
                  to={`/category/${encodeURIComponent(product.categorySlug)}`}
                  className="text-sm font-medium text-blue-700 hover:underline"
                  data-testid={`product-card-category-${product.id}`}
                >
                  View category
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const ITEMS_PER_PAGE = 24;

function Pagination({ currentPage, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  const getPageNumbers = () => {
    const pages = [];
    const showEllipsis = totalPages > 7;

    if (!showEllipsis) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push('...');
      for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
        pages.push(i);
      }
      if (currentPage < totalPages - 2) pages.push('...');
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div className="mt-8 flex items-center justify-center gap-2">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="rounded-md border px-3 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
        data-testid="pagination-prev"
      >
        Previous
      </button>
      <div className="flex items-center gap-1">
        {getPageNumbers().map((page, idx) =>
          page === '...' ? (
            <span key={`ellipsis-${idx}`} className="px-2 text-slate-400">...</span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={`min-w-[40px] rounded-md px-3 py-2 text-sm font-medium ${
                page === currentPage
                  ? 'bg-blue-600 text-white'
                  : 'border hover:bg-slate-50'
              }`}
              data-testid={`pagination-page-${page}`}
            >
              {page}
            </button>
          )
        )}
      </div>
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="rounded-md border px-3 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
        data-testid="pagination-next"
      >
        Next
      </button>
    </div>
  );
}

export default function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get('q') || '';
  const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10));

  const { addItem } = useCart();
  const { toggle: toggleWishlist, isInWishlist } = useWishlist();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);

  const products = useMemo(() => {
    const items = data?.items;
    return Array.isArray(items) ? items : [];
  }, [data]);

  const totalPages = useMemo(() => {
    const total = data?.total || 0;
    return Math.ceil(total / ITEMS_PER_PAGE);
  }, [data]);

  const handlePageChange = (newPage) => {
    const params = {};
    if (q) params.q = q;
    if (newPage > 1) params.page = String(newPage);
    setSearchParams(params);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoading(true);
      setError('');
      try {
        const offset = (page - 1) * ITEMS_PER_PAGE;
        const res = await listProducts({ q: q || undefined, limit: ITEMS_PER_PAGE, offset });
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load products');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [q, page]);

  return (
    <div className="container-page py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Featured products</h1>
          <p className="mt-1 text-sm text-slate-600">Browse the catalog and discover deals.</p>
        </div>

        <form
          className="flex w-full max-w-md items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const nextQ = String(form.get('q') || '').trim();
            setSearchParams(nextQ ? { q: nextQ } : {});
          }}
        >
          <input
            name="q"
            defaultValue={q}
            placeholder="Search products"
            className="w-full rounded-lg border px-3 py-2 text-sm focus-ring"
            data-testid="home-search-input"
          />
          <Button type="submit" data-testid="home-search-submit">
            Search
          </Button>
        </form>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner />
          </div>
        ) : error ? (
          <Alert variant="error">{error}</Alert>
        ) : products.length === 0 ? (
          <EmptyState
            title="No products found"
            description={q ? `No results for "${q}". Try a different search.` : 'No products are available yet.'}
            data-testid="home-empty"
          />
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between text-sm text-slate-600">
              <span>
                Showing {(page - 1) * ITEMS_PER_PAGE + 1}–{Math.min(page * ITEMS_PER_PAGE, data?.total || 0)} of {data?.total?.toLocaleString() || 0} products
              </span>
              <span>Page {page} of {totalPages}</span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {products.map((p) => (
                <ProductCard
                  key={p.id || p.sku}
                  product={p}
                  inWishlist={isInWishlist(p?.id)}
                  onAddToCart={(product) => addItem(product, 1)}
                  onToggleWishlist={(product) => toggleWishlist(product)}
                />
              ))}
            </div>
            <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
          </>
        )}
      </div>
    </div>
  );
}
