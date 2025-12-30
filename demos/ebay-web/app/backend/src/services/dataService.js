import { config } from '../config/env.js';
import { tryQuery } from '../db/pool.js';
import { categories as mockCategories, products as mockProducts, demoUser } from '../data/mockData.js';
import * as sqliteDb from '../db/sqliteDb.js';
import { logger } from '../utils/logger.js';

function computeCategoryPathText(categoryPathArr) {
  return categoryPathArr.join('/');
}

function normalizeProduct(p) {
  return {
    ...p,
    price: typeof p.price === 'string' ? parseFloat(p.price) : p.price,
    categoryPathText: computeCategoryPathText(p.categoryPath)
  };
}

export async function dbAvailable() {
  if (config.DEMO_MODE) return false;
  if (!config.DATABASE_URL) return false;
  try {
    await tryQuery('SELECT 1');
    return true;
  } catch (e) {
    logger.warn('DB unavailable, falling back to in-memory demo data', { message: e.message });
    return false;
  }
}

export async function getCategoriesTree() {
  // Try SQLite first
  const sqliteCategories = await sqliteDb.getCategories();
  if (sqliteCategories.length > 0) {
    return sqliteCategories;
  }

  // Fallback to mock data
  return mockCategories;
}

export async function getCategoryBySlug(slug) {
  // Try SQLite first
  const category = await sqliteDb.getCategoryBySlug(slug);
  if (category) {
    return category;
  }

  // Fallback to mock data
  const tree = mockCategories;
  const stack = [...tree];
  while (stack.length) {
    const node = stack.shift();
    if (node.slug === slug) return node;
    if (node.children?.length) stack.push(...node.children);
  }
  return null;
}

export async function listProducts({ q, limit = 20, offset = 0, sort = 'position' } = {}) {
  // Try SQLite first
  const sqliteResult = await sqliteDb.listProducts({ q, limit, offset, sort });
  if (sqliteResult.total > 0 || await sqliteDb.sqliteAvailable()) {
    return {
      ...sqliteResult,
      items: sqliteResult.items.map(normalizeProduct)
    };
  }

  // Fallback to mock data
  const all = mockProducts.map(normalizeProduct);
  let filtered = all;
  if (q) {
    const qq = q.toLowerCase();
    filtered = filtered.filter(
      (p) =>
        p.name.toLowerCase().includes(qq) ||
        p.sku.toLowerCase().includes(qq) ||
        p.description.toLowerCase().includes(qq) ||
        p.shortDescription.toLowerCase().includes(qq)
    );
  }

  filtered = sortProducts(filtered, sort);

  const total = filtered.length;
  const items = filtered.slice(offset, offset + limit);
  return { total, items, limit, offset };
}

export async function getProductById(id) {
  // Try SQLite first
  const product = await sqliteDb.getProductById(id);
  if (product) {
    return normalizeProduct(product);
  }

  // Fallback to mock data
  const p = mockProducts.find((x) => x.id === id);
  return p ? normalizeProduct(p) : null;
}

export function sortProducts(items, sort) {
  const arr = [...items];
  if (sort === 'price_asc') arr.sort((a, b) => a.price - b.price);
  else if (sort === 'price_desc') arr.sort((a, b) => b.price - a.price);
  else if (sort === 'rating_desc') arr.sort((a, b) => (b.rating || 0) - (a.rating || 0));
  return arr;
}

export async function listProductsByCategorySlug({ slug, limit = 20, offset = 0, sort = 'position' }) {
  // Try SQLite first
  const sqliteResult = await sqliteDb.listProductsByCategory({ slug, limit, offset, sort });
  if (sqliteResult.total > 0 || await sqliteDb.sqliteAvailable()) {
    return {
      ...sqliteResult,
      items: sqliteResult.items.map(normalizeProduct)
    };
  }

  // Fallback to mock data
  const all = mockProducts.map(normalizeProduct);

  let filtered = all;
  if (slug && slug !== 'all') {
    filtered = all.filter((p) => p.categoryPath.includes(slug));
  }

  filtered = sortProducts(filtered, sort);
  const total = filtered.length;
  const items = filtered.slice(offset, offset + limit);
  return { total, items, limit, offset, categorySlug: slug };
}

export async function advancedSearch(filters) {
  // Try SQLite first
  const sqliteResult = await sqliteDb.advancedSearch(filters);
  if (sqliteResult.total > 0 || await sqliteDb.sqliteAvailable()) {
    return {
      ...sqliteResult,
      items: sqliteResult.items.map(normalizeProduct)
    };
  }

  // Fallback to mock data
  const {
    name,
    sku,
    description,
    shortDescription,
    minPrice,
    maxPrice,
    limit = 50,
    offset = 0,
    sort = 'position'
  } = filters;

  let filtered = mockProducts.map(normalizeProduct);

  const like = (text, needle) => text.toLowerCase().includes(String(needle).toLowerCase());

  if (name) filtered = filtered.filter((p) => like(p.name, name));
  if (sku) filtered = filtered.filter((p) => like(p.sku, sku));
  if (description) filtered = filtered.filter((p) => like(p.description, description));
  if (shortDescription) filtered = filtered.filter((p) => like(p.shortDescription, shortDescription));

  const min = minPrice !== undefined && minPrice !== null && minPrice !== '' ? Number(minPrice) : null;
  const max = maxPrice !== undefined && maxPrice !== null && maxPrice !== '' ? Number(maxPrice) : null;

  if (Number.isFinite(min)) filtered = filtered.filter((p) => p.price >= min);
  if (Number.isFinite(max)) filtered = filtered.filter((p) => p.price <= max);

  filtered = sortProducts(filtered, sort);

  const total = filtered.length;
  const items = filtered.slice(offset, offset + limit);
  return { total, items, limit, offset };
}

export async function getDemoUser() {
  return demoUser;
}
