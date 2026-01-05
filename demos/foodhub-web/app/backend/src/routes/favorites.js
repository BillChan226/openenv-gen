import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, listOk, ok } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT r.id, r.category_id, r.name, r.description, r.price_range, r.rating, r.reviews_count,
              r.distance_miles, r.delivery_time_min, r.delivery_fee_cents, r.minimum_order_cents,
              r.cover_image_url, r.hero_image_url, r.is_active
       FROM favorites f
       JOIN restaurants r ON r.id = f.restaurant_id
       WHERE f.user_id = $1
       ORDER BY f.created_at DESC`,
      [req.user.id]
    );

    const items = rowsToCamel(rows).map((r) => ({
      id: r.id,
      categoryId: r.categoryId,
      name: r.name,
      description: r.description ?? null,
      priceRange: r.priceRange,
      rating: Number(r.rating),
      reviewsCount: r.reviewsCount,
      distanceMiles: Number(r.distanceMiles),
      deliveryTimeMin: r.deliveryTimeMin,
      deliveryFeeCents: r.deliveryFeeCents,
      minimumOrderCents: r.minimumOrderCents,
      coverImageUrl: r.coverImageUrl ?? null,
      heroImageUrl: r.heroImageUrl ?? null,
      isActive: r.isActive
    }));

    return listOk(res, items, { limit: items.length, offset: 0, total: items.length });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const body = z.object({ restaurantId: z.string().uuid() }).parse(req.body);

    await query(
      `INSERT INTO favorites (user_id, restaurant_id)
       VALUES ($1, $2)
       ON CONFLICT (user_id, restaurant_id) DO NOTHING`,
      [req.user.id, body.restaurantId]
    );

    return ok(res, { favorited: true });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:restaurantId', requireAuth, async (req, res, next) => {
  try {
    const restaurantId = z.string().uuid().parse(req.params.restaurantId);

    const del = await query('DELETE FROM favorites WHERE user_id = $1 AND restaurant_id = $2', [
      req.user.id,
      restaurantId
    ]);

    if (!del.rowCount) throw new ApiError('NOT_FOUND', 'Favorite not found', 404);

    return ok(res, { deleted: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
