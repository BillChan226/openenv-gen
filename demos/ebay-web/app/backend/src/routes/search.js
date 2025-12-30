import express from 'express';
import { body, query } from 'express-validator';

import { validate } from '../middleware/validators.js';
import { advancedSearch } from '../services/dataService.js';

const router = express.Router();


// Basic search endpoint: /api/search?q=...
// Backward-compatible alias that proxies to the advanced search service.
router.get(
  '/',
  validate([
    query('q').exists({ checkFalsy: true }).isString().trim(),
    query('limit').optional().isInt({ min: 1, max: 100 }).toInt(),
    query('offset').optional().isInt({ min: 0 }).toInt(),
    query('sort').optional().isString().trim()
  ]),
  async (req, res, next) => {
    try {
      const q = String(req.query.q || '').trim();
      if (!q) {
        return res.status(400).json({ error: 'Missing required query parameter: q' });
      }

      const payload = {
        name: q,
        limit: req.query.limit,
        offset: req.query.offset,
        sort: req.query.sort
      };

      const result = await advancedSearch(payload);
      return res.json(result);
    } catch (e) {
      return next(e);
    }
  }
);

// OpenAPI contract: /api/search/advanced
// Support both GET (query params) and POST (JSON body)
router.get(
  '/advanced',
  validate([
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
      const payload = { ...(req.query || {}) };
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

router.post(
  '/advanced',
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

export default router;
