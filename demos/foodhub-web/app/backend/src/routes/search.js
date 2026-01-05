import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { listOk } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';

const router = Router();

router.get('/suggestions', async (req, res, next) => {
  try {
    const q = z.string().min(1).parse(req.query.q);
    const limit = z.coerce.number().int().min(1).max(20).default(8).parse(req.query.limit ?? 8);

    const restaurantsRes = await query(
      `SELECT id, name FROM restaurants WHERE is_active = true AND name ILIKE $1 ORDER BY rating DESC LIMIT $2`,
      [`%${q}%`, limit]
    );

    const menuItemsRes = await query(
      `SELECT mi.id, mi.name, mi.restaurant_id, r.name AS restaurant_name
       FROM menu_items mi
       JOIN restaurants r ON r.id = mi.restaurant_id
       WHERE mi.is_available = true AND mi.name ILIKE $1
       ORDER BY mi.created_at DESC
       LIMIT $2`,
      [`%${q}%`, limit]
    );

    const restaurants = rowsToCamel(restaurantsRes.rows).map((r) => ({
      type: 'restaurant',
      id: r.id,
      name: r.name
    }));

    const items = rowsToCamel(menuItemsRes.rows).map((i) => ({
      type: 'menuItem',
      id: i.id,
      name: i.name,
      restaurantId: i.restaurantId,
      restaurantName: i.restaurantName
    }));

    const suggestions = [...restaurants, ...items].slice(0, limit);
    return listOk(res, suggestions, { limit, offset: 0, total: suggestions.length });
  } catch (err) {
    return next(err);
  }
});

export default router;
