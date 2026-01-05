import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { listOk, ok } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT id, query_text, created_at
       FROM recent_searches
       WHERE user_id = $1
       ORDER BY created_at DESC
       LIMIT 10`,
      [req.user.id]
    );

    const items = rowsToCamel(rows).map((r) => ({
      id: r.id,
      queryText: r.queryText,
      createdAt: r.createdAt
    }));

    return listOk(res, items, { limit: 10, offset: 0, total: items.length });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const body = z.object({ queryText: z.string().min(1).max(80) }).parse(req.body);

    await query(
      `INSERT INTO recent_searches (user_id, query_text)
       VALUES ($1, $2)`,
      [req.user.id, body.queryText]
    );

    return ok(res, { saved: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
