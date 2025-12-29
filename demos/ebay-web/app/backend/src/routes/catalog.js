import express from 'express';
import { body, param, query } from 'express-validator';

import { validate } from '../middleware/validators.js';
import { ApiError } from '../middleware/errorHandler.js';
import {
  getCategoriesTree,
  getCategoryBySlug,
  listProducts,
  getProductById,
  listProductsByCategorySlug,
  advancedSearch
} from '../services/dataService.js';

const router = express.Router();


// Root catalog summary
// Compatibility endpoint for clients that call GET /api/catalog
router.get('/', async (req, res, next) => {
  try {
    const [categories, products] = await Promise.all([
      getCategoriesTree(),
      // Provide a small default set of products for landing pages
      listProducts({ limit: 12, offset: 0 })
    ]);

    return res.json({
      categories: { items: categories },
      items: products.items ?? products.products ?? [],
      total: products.total ?? (products.items ? products.items.length : 0)
    });
  } catch (e) {
    return next(e);
  }
});

// Compatibility endpoint for clients that call GET /api/catalog/items
// Alias to GET /api/catalog/products
router.get(
  '/items',
  validate([
    query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    query('offset').optional().isInt({ min: 0 }).toInt(),
    query('q').optional().isString().trim(),
    query('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const { q, sort } = req.query;
      const limit = req.query.limit ?? 20;
      const offset = req.query.offset ?? 0;
      const result = await listProducts({ q, sort, limit, offset });
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

// Categories tree
// Compatibility: some clients expect GET /api/categories (without /tree)
router.get('/categories', async (req, res, next) => {
  try {
    const tree = await getCategoriesTree();
    return res.json({ items: tree });
  } catch (e) {
    return next(e);
  }
});

router.get('/categories/tree', async (req, res, next) => {
  try {
    const tree = await getCategoriesTree();
    return res.json({ items: tree });
  } catch (e) {
    return next(e);
  }
});

// Category by slug
router.get(
  '/categories/:slug',
  validate([param('slug').trim().notEmpty().withMessage('slug is required')]),
  async (req, res, next) => {
    try {
      const cat = await getCategoryBySlug(req.params.slug);
      if (!cat) throw ApiError.notFound('Category not found');
      return res.json({ item: cat });
    } catch (e) {
      return next(e);
    }
  }
);

// Products listing (optionally q)
router.get(
  '/products',
  validate([
    query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    query('offset').optional().isInt({ min: 0 }).toInt(),
    query('q').optional().isString().trim(),
    query('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const { q, sort } = req.query;
      const limit = req.query.limit ?? 20;
      const offset = req.query.offset ?? 0;
      const result = await listProducts({ q, sort, limit, offset });
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

// Product by id
router.get(
  '/products/:id',
  validate([param('id').trim().notEmpty().withMessage('id is required')]),
  async (req, res, next) => {
    try {
      const p = await getProductById(req.params.id);
      if (!p) throw ApiError.notFound('Product not found');
      return res.json({ item: p });
    } catch (e) {
      return next(e);
    }
  }
);

// Category product listing with sorting/pagination
router.get(
  '/categories/:slug/products',
  validate([
    param('slug').trim().notEmpty().withMessage('slug is required'),
    query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    query('offset').optional().isInt({ min: 0 }).toInt(),
    query('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const limit = req.query.limit ?? 20;
      const offset = req.query.offset ?? 0;
      const sort = req.query.sort || 'position';
      const result = await listProductsByCategorySlug({
        slug: req.params.slug,
        limit,
        offset,
        sort
      });
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

// Advanced search
// POST supports complex payloads
router.post(
  '/search/advanced',
  validate([
    body('name').optional().isString().trim(),
    body('sku').optional().isString().trim(),
    body('description').optional().isString().trim(),
    body('shortDescription').optional().isString().trim(),
    body('minPrice').optional().isFloat({ min: 0 }).toFloat(),
    body('maxPrice').optional().isFloat({ min: 0 }).toFloat(),
    body('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    body('offset').optional().isInt({ min: 0 }).toInt(),
    body('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const result = await advancedSearch(req.body || {});
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

// GET compatibility for typical search clients (query params)
router.get(
  '/search/advanced',
  validate([
    // Support both `q`/`query` and explicit fields
    query('q').optional().isString().trim(),
    query('query').optional().isString().trim(),
    query('name').optional().isString().trim(),
    query('sku').optional().isString().trim(),
    query('description').optional().isString().trim(),
    query('shortDescription').optional().isString().trim(),
    query('minPrice').optional().isFloat({ min: 0 }).toFloat(),
    query('maxPrice').optional().isFloat({ min: 0 }).toFloat(),
    query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    query('offset').optional().isInt({ min: 0 }).toInt(),
    query('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const payload = {
        ...(req.query || {})
      };

      // Map common client param names to our service fields
      const q = payload.q ?? payload.query;
      if (q && !payload.name) payload.name = q;

      // Ensure numeric conversions if validators didn't run for some reason
      if (payload.minPrice != null) payload.minPrice = Number(payload.minPrice);
      if (payload.maxPrice != null) payload.maxPrice = Number(payload.maxPrice);
      if (payload.limit != null) payload.limit = Number.parseInt(String(payload.limit), 10);
      if (payload.offset != null) payload.offset = Number.parseInt(String(payload.offset), 10);

      const result = await advancedSearch(payload);
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

export default router;
