import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { TOP_CATEGORIES } from '../../data/categories.js';
import { getCategoriesTree } from '../../services/api.js';

function normalizeTree(tree) {
  // Accept various shapes: {categories:[...]}, [...], {items:[...]}
  const cats = Array.isArray(tree) ? tree : tree?.categories || tree?.items || [];
  return cats;
}

export function CategoriesNav() {
  const [openSlug, setOpenSlug] = useState(null);
  const [tree, setTree] = useState([]);

  useEffect(() => {
    let mounted = true;
    getCategoriesTree()
      .then((data) => {
        if (!mounted) return;
        setTree(normalizeTree(data));
      })
      .catch(() => {
        // ignore; fallback to static
      });
    return () => {
      mounted = false;
    };
  }, []);

  const treeBySlug = useMemo(() => {
    const map = new Map();
    for (const c of tree) {
      if (c?.slug) map.set(c.slug, c);
    }
    return map;
  }, [tree]);

  function close() {
    setOpenSlug(null);
  }

  return (
    <nav className="relative">
      <ul className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2 text-[13px] text-gray-800">
        {TOP_CATEGORIES.map((c) => {
          const active = openSlug === c.slug;
          return (
            <li
              key={c.slug}
              className="relative"
              onMouseEnter={() => setOpenSlug(c.slug)}
              onMouseLeave={close}
            >
              <Link
                to={`/category/${c.slug}`}
                className="inline-flex items-center gap-1 rounded px-1 py-1 hover:text-brand-blue focus-ring"
                data-testid={`nav-category-${c.slug}`}
              >
                {c.name}
                <ChevronDown className="h-3.5 w-3.5 text-gray-500" aria-hidden="true" />
              </Link>

              {active ? (
                <div
                  className="absolute left-0 top-full mt-2 w-[560px] max-w-[calc(100vw-2rem)] rounded border border-gray-200 bg-white p-4 shadow-lg"
                  role="menu"
                  data-testid={`nav-mega-${c.slug}`}
                >
                  <MegaMenuContent category={treeBySlug.get(c.slug)} fallbackSlug={c.slug} onNavigate={close} />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function MegaMenuContent({ category, fallbackSlug, onNavigate }) {
  const subs = category?.children || category?.subcategories || [];
  const left = subs.slice(0, 8);
  const right = subs[0]?.children || subs[0]?.subcategories || [];

  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <div className="text-xs font-semibold text-gray-900">Shop By</div>
        <ul className="mt-2 space-y-2 text-sm">
          {left.length ? (
            left.map((s) => (
              <li key={s.slug || s.name}>
                <Link
                  to={`/category/${s.slug || fallbackSlug}`}
                  className="text-gray-900 hover:text-brand-blue hover:underline"
                  onClick={onNavigate}
                  data-testid={`nav-subcategory-${fallbackSlug}-${s.slug || s.name}`}
                >
                  {s.name}
                </Link>
              </li>
            ))
          ) : (
            <li className="text-gray-600">Popular subcategories</li>
          )}
        </ul>
      </div>
      <div>
        <div className="text-xs font-semibold text-gray-900">More</div>
        <ul className="mt-2 space-y-2 text-sm">
          {right.length ? (
            right.slice(0, 10).map((s) => (
              <li key={s.slug || s.name}>
                <Link
                  to={`/category/${s.slug || fallbackSlug}`}
                  className="text-gray-700 hover:text-brand-blue hover:underline"
                  onClick={onNavigate}
                  data-testid={`nav-leaf-${fallbackSlug}-${s.slug || s.name}`}
                >
                  {s.name}
                </Link>
              </li>
            ))
          ) : (
            <li className="text-gray-600">Browse all items</li>
          )}
        </ul>
      </div>
    </div>
  );
}
