import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { getCategoryBySlug, listCategoryProducts } from '../services/api.js';
import { Spinner } from '../components/ui/Spinner.jsx';
import { Alert } from '../components/ui/Alert.jsx';
import { EmptyState } from '../components/ui/EmptyState.jsx';

const ITEMS_PER_PAGE = 24;

function formatPrice(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value ?? '');
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(n);
}

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

export default function CategoryPage() {
  const { slug } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [category, setCategory] = useState(null);
  const [productsData, setProductsData] = useState(null);

  const products = useMemo(() => {
    const items = productsData?.items;
    return Array.isArray(items) ? items : [];
  }, [productsData]);

  const totalPages = useMemo(() => {
    const total = productsData?.total || 0;
    return Math.ceil(total / ITEMS_PER_PAGE);
  }, [productsData]);

  const handlePageChange = (newPage) => {
    if (newPage > 1) {
      setSearchParams({ page: String(newPage) });
    } else {
      setSearchParams({});
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoading(true);
      setError('');
      try {
        const offset = (page - 1) * ITEMS_PER_PAGE;
        const [catRes, prodRes] = await Promise.all([
          getCategoryBySlug(slug),
          listCategoryProducts(slug, { limit: ITEMS_PER_PAGE, offset })
        ]);
        if (!cancelled) {
          setCategory(catRes?.item || null);
          setProductsData(prodRes);
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load category');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [slug, page]);

  return (
    <div className="container-page py-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{category?.name || 'Category'}</h1>
          <p className="mt-1 text-sm text-slate-600">Slug: {slug}</p>
        </div>
        <Link
          to="/"
          className="text-sm font-medium text-blue-700 hover:underline"
          data-testid="category-back-home"
        >
          Back to home
        </Link>
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
            title="No products in this category"
            description="Try another category from the navigation."
            data-testid="category-empty"
          />
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between text-sm text-slate-600">
              <span>
                Showing {(page - 1) * ITEMS_PER_PAGE + 1}–{Math.min(page * ITEMS_PER_PAGE, productsData?.total || 0)} of {productsData?.total?.toLocaleString() || 0} products
              </span>
              <span>Page {page} of {totalPages}</span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {products.map((p) => (
                <div key={p.id || p.sku} className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
                  {p?.image && (
                    <div className="mb-3 aspect-square overflow-hidden rounded-md bg-gray-100">
                      <img
                        src={p.image}
                        alt={p.name}
                        className="h-full w-full object-contain"
                        loading="lazy"
                      />
                    </div>
                  )}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="line-clamp-2 text-sm font-semibold text-slate-900">{p?.name}</div>
                      <div className="mt-1 text-xs text-slate-500">SKU: {p?.sku || '—'}</div>
                    </div>
                    <div className="text-sm font-bold text-green-700">{formatPrice(p?.price)}</div>
                  </div>
                  {p?.rating && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-slate-600">
                      <span className="text-yellow-500">★</span>
                      <span>{p.rating}</span>
                      {p?.reviewCount > 0 && <span className="text-slate-400">({p.reviewCount.toLocaleString()} reviews)</span>}
                    </div>
                  )}
                  {p?.shortDescription ? (
                    <p className="mt-2 line-clamp-2 text-xs text-slate-600">{p.shortDescription}</p>
                  ) : null}
                </div>
              ))}
            </div>
            <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
          </>
        )}
      </div>
    </div>
  );
}
