import { Router } from 'express';

import { query } from '../db.js';
import { assert } from '../utils/validation.js';
import { okList } from '../utils/response.js';

const router = Router();

router.get('/locations', async (req, res, next) => {
  try {
    const q = (req.query.q || '').toString().trim();
    const limit = Math.min(100, Math.max(1, Number(req.query.limit || 10)));

    assert(q.length >= 1, 'Invalid input', { field: 'q' });

    const { rows } = await query(
      `SELECT id, code, label, type, country_code, region, lat, lng
       FROM locations
       WHERE code ILIKE $1 OR label ILIKE $1
       ORDER BY CASE WHEN code ILIKE $2 THEN 0 ELSE 1 END, label ASC
       LIMIT $3`,
      [`%${q}%`, `${q}%`, limit]
    );

    return okList(res, { items: rows, total: rows.length, limit, offset: 0 });
  } catch (err) {
    return next(err);
  }
});

export default router;
