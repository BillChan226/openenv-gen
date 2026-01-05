import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { listOk } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';

const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const includeEmpty = z.coerce.boolean().default(true).parse(req.query.includeEmpty ?? 'true');

    if (includeEmpty) {
      const { rows } = await query(
        'SELECT id, name, emoji, sort_order FROM restaurant_categories ORDER BY sort_order ASC, name ASC'
      );
      const items = rowsToCamel(rows).map((c) => ({
        id: c.id,
        name: c.name,
        emoji: c.emoji,
        sortOrder: c.sortOrder
      }));
      return listOk(res, items, { limit: items.length, offset: 0, total: items.length });
    }

    const { rows } = await query(
      `SELECT rc.id, rc.name, rc.emoji, rc.sort_order
       FROM restaurant_categories rc
       WHERE EXISTS (SELECT 1 FROM restaurants r WHERE r.category_id = rc.id AND r.is_active = true)
       ORDER BY rc.sort_order ASC, rc.name ASC`
    );

    const items = rowsToCamel(rows).map((c) => ({
      id: c.id,
      name: c.name,
      emoji: c.emoji,
      sortOrder: c.sortOrder
    }));

    return listOk(res, items, { limit: items.length, offset: 0, total: items.length });
  } catch (err) {
    return next(err);
  }
});

export default router;
