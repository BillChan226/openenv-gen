import initSqlJs from 'sql.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { logger } from '../utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DB_PATH = path.resolve(__dirname, '../../..', 'database', 'products.db');

let db = null;
let initPromise = null;

async function initDb() {
  if (db) return db;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    try {
      if (!fs.existsSync(DB_PATH)) {
        logger.warn(`SQLite database not found: ${DB_PATH}`);
        return null;
      }

      const SQL = await initSqlJs();
      const buffer = fs.readFileSync(DB_PATH);
      db = new SQL.Database(buffer);
      logger.info(`SQLite database loaded: ${DB_PATH}`);
      return db;
    } catch (err) {
      logger.error(`Failed to initialize SQLite: ${err.message}`);
      return null;
    }
  })();

  return initPromise;
}

export async function getProductsDb() {
  return initDb();
}

export async function sqliteAvailable() {
  const conn = await getProductsDb();
  if (!conn) return false;

  try {
    conn.exec('SELECT 1');
    return true;
  } catch {
    return false;
  }
}

export async function getCategories() {
  const conn = await getProductsDb();
  if (!conn) return [];

  try {
    const result = conn.exec(`
      SELECT id, name, slug, parent_id
      FROM categories
      ORDER BY name
    `);

    if (!result.length) return [];

    const rows = result[0].values.map(row => ({
      id: row[0],
      name: row[1],
      slug: row[2],
      parent_id: row[3]
    }));

    // Build tree structure
    const categories = rows.map(row => ({
      id: row.id,
      name: row.name,
      slug: row.slug,
      children: []
    }));

    return categories;
  } catch (err) {
    logger.error('Error fetching categories from SQLite', { error: err.message });
    return [];
  }
}

export async function getCategoryBySlug(slug) {
  const conn = await getProductsDb();
  if (!conn) return null;

  try {
    const stmt = conn.prepare(`
      SELECT id, name, slug, parent_id
      FROM categories
      WHERE slug = ?
    `);
    stmt.bind([slug]);

    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return {
        id: row.id,
        name: row.name,
        slug: row.slug,
        children: []
      };
    }
    stmt.free();
    return null;
  } catch (err) {
    logger.error('Error fetching category from SQLite', { error: err.message });
    return null;
  }
}

function rowToProduct(row) {
  return {
    id: row.id,
    sku: row.sku,
    name: row.name,
    price: row.price,
    rating: row.rating,
    reviewCount: row.review_count,
    image: row.image,
    shortDescription: row.short_description || '',
    description: row.description || '',
    features: JSON.parse(row.features || '[]'),
    details: JSON.parse(row.details || '{}'),
    categoryPath: [row.category_slug],
    subCategory: row.sub_category || ''
  };
}

function execToObjects(result) {
  if (!result.length) return [];
  const columns = result[0].columns;
  return result[0].values.map(row => {
    const obj = {};
    columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}

export async function listProducts({ q, limit = 20, offset = 0, sort = 'position' } = {}) {
  const conn = await getProductsDb();
  if (!conn) return { total: 0, items: [], limit, offset };

  try {
    let orderBy = 'review_count DESC';
    if (sort === 'price_asc') orderBy = 'price ASC';
    else if (sort === 'price_desc') orderBy = 'price DESC';
    else if (sort === 'rating_desc') orderBy = 'rating DESC';

    let rows, total;

    if (q) {
      // Use LIKE for text search (sql.js doesn't support FTS well)
      const searchTerm = `%${q.replace(/[^\w\s]/g, ' ').trim()}%`;

      const countResult = conn.exec(`
        SELECT COUNT(*) as count FROM products
        WHERE name LIKE '${searchTerm}' OR sku LIKE '${searchTerm}'
           OR short_description LIKE '${searchTerm}' OR description LIKE '${searchTerm}'
      `);
      total = countResult.length ? countResult[0].values[0][0] : 0;

      const result = conn.exec(`
        SELECT * FROM products
        WHERE name LIKE '${searchTerm}' OR sku LIKE '${searchTerm}'
           OR short_description LIKE '${searchTerm}' OR description LIKE '${searchTerm}'
        ORDER BY ${orderBy}
        LIMIT ${limit} OFFSET ${offset}
      `);
      rows = execToObjects(result);
    } else {
      const countResult = conn.exec('SELECT COUNT(*) as count FROM products');
      total = countResult.length ? countResult[0].values[0][0] : 0;

      const result = conn.exec(`
        SELECT * FROM products
        ORDER BY ${orderBy}
        LIMIT ${limit} OFFSET ${offset}
      `);
      rows = execToObjects(result);
    }

    const items = rows.map(rowToProduct);
    return { total, items, limit, offset };
  } catch (err) {
    logger.error('Error listing products from SQLite', { error: err.message });
    return { total: 0, items: [], limit, offset };
  }
}

export async function getProductById(id) {
  const conn = await getProductsDb();
  if (!conn) return null;

  try {
    const stmt = conn.prepare('SELECT * FROM products WHERE id = ?');
    stmt.bind([id]);

    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return rowToProduct(row);
    }
    stmt.free();
    return null;
  } catch (err) {
    logger.error('Error fetching product from SQLite', { error: err.message });
    return null;
  }
}

export async function listProductsByCategory({ slug, limit = 20, offset = 0, sort = 'position' }) {
  const conn = await getProductsDb();
  if (!conn) return { total: 0, items: [], limit, offset, categorySlug: slug };

  try {
    let orderBy = 'review_count DESC';
    if (sort === 'price_asc') orderBy = 'price ASC';
    else if (sort === 'price_desc') orderBy = 'price DESC';
    else if (sort === 'rating_desc') orderBy = 'rating DESC';

    let rows, total;

    if (slug && slug !== 'all') {
      const countResult = conn.exec(`
        SELECT COUNT(*) as count FROM products WHERE category_slug = '${slug}'
      `);
      total = countResult.length ? countResult[0].values[0][0] : 0;

      const result = conn.exec(`
        SELECT * FROM products
        WHERE category_slug = '${slug}'
        ORDER BY ${orderBy}
        LIMIT ${limit} OFFSET ${offset}
      `);
      rows = execToObjects(result);
    } else {
      const countResult = conn.exec('SELECT COUNT(*) as count FROM products');
      total = countResult.length ? countResult[0].values[0][0] : 0;

      const result = conn.exec(`
        SELECT * FROM products
        ORDER BY ${orderBy}
        LIMIT ${limit} OFFSET ${offset}
      `);
      rows = execToObjects(result);
    }

    const items = rows.map(rowToProduct);
    return { total, items, limit, offset, categorySlug: slug };
  } catch (err) {
    logger.error('Error listing products by category from SQLite', { error: err.message });
    return { total: 0, items: [], limit, offset, categorySlug: slug };
  }
}

export async function advancedSearch(filters) {
  const conn = await getProductsDb();
  if (!conn) return { total: 0, items: [], limit: 50, offset: 0 };

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

  try {
    let orderBy = 'review_count DESC';
    if (sort === 'price_asc') orderBy = 'price ASC';
    else if (sort === 'price_desc') orderBy = 'price DESC';
    else if (sort === 'rating_desc') orderBy = 'rating DESC';

    const conditions = [];

    if (name) {
      conditions.push(`name LIKE '%${name.replace(/'/g, "''")}%'`);
    }
    if (sku) {
      conditions.push(`sku LIKE '%${sku.replace(/'/g, "''")}%'`);
    }
    if (description) {
      conditions.push(`description LIKE '%${description.replace(/'/g, "''")}%'`);
    }
    if (shortDescription) {
      conditions.push(`short_description LIKE '%${shortDescription.replace(/'/g, "''")}%'`);
    }

    const min = minPrice !== undefined && minPrice !== null && minPrice !== '' ? Number(minPrice) : null;
    const max = maxPrice !== undefined && maxPrice !== null && maxPrice !== '' ? Number(maxPrice) : null;

    if (Number.isFinite(min)) {
      conditions.push(`price >= ${min}`);
    }
    if (Number.isFinite(max)) {
      conditions.push(`price <= ${max}`);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    const countResult = conn.exec(`SELECT COUNT(*) as count FROM products ${whereClause}`);
    const total = countResult.length ? countResult[0].values[0][0] : 0;

    const result = conn.exec(`
      SELECT * FROM products
      ${whereClause}
      ORDER BY ${orderBy}
      LIMIT ${limit} OFFSET ${offset}
    `);
    const rows = execToObjects(result);

    const items = rows.map(rowToProduct);
    return { total, items, limit, offset };
  } catch (err) {
    logger.error('Error in advanced search', { error: err.message });
    return { total: 0, items: [], limit, offset };
  }
}
