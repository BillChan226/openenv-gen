import { Router } from 'express';

import { query } from '../db.js';
import { requireAuth } from '../middleware/auth.js';
import { assert } from '../utils/validation.js';
import { okList } from '../utils/response.js';

const router = Router();

router.get('/favorites', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT id, user_id, item_type, item_id, created_at
       FROM favorites
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [req.user.id]
    );

    return okList(res, { items: rows, total: rows.length, limit: rows.length, offset: 0 });
  } catch (err) {
    return next(err);
  }
});

router.post('/favorites', requireAuth, async (req, res, next) => {
  try {
    const { item_type } = req.body || {};
    assert(typeof item_type === 'string', 'Invalid input', { field: 'item_type' });

    const allowed = new Set(['hotel', 'flight', 'car', 'package']);
    assert(allowed.has(item_type), 'Invalid input', { field: 'item_type' });

    // Spec expects item_id; accept legacy payloads (hotel_id/flight_id/...) and map them.
    const item_id =
      req.body?.item_id ??
      req.body?.hotel_id ??
      req.body?.flight_id ??
      req.body?.car_id ??
      req.body?.package_id;

    assert(typeof item_id === 'string' && item_id.length > 0, 'Invalid input', { field: 'item_id' });

    const vals = [req.user.id, item_type, item_id];

    const { rows } = await query(
      `INSERT INTO favorites (user_id, item_type, item_id)
       VALUES ($1, $2, $3)
       ON CONFLICT DO NOTHING
       RETURNING id, user_id, item_type, item_id, created_at`,
      vals
    );

    const favorite = rows[0];
    if (!favorite) {
      const existing = await query(
        `SELECT id, user_id, item_type, item_id, created_at
         FROM favorites
         WHERE user_id = $1 AND item_type = $2 AND item_id = $3`,
        vals
      );
      return res.status(200).json({ favorite: existing.rows[0] });
    }

    return res.status(201).json({ favorite });
  } catch (err) {
    return next(err);
  }
});

router.delete('/favorites/:favorite_id', requireAuth, async (req, res, next) => {
  try {
    const { favorite_id } = req.params;

    await query('DELETE FROM favorites WHERE id = $1 AND user_id = $2', [favorite_id, req.user.id]);
    return res.status(204).send();
  } catch (err) {
    return next(err);
  }
});

export default router;
