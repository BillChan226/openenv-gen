import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, listOk, ok } from '../utils/response.js';
import { rowToCamel, rowsToCamel } from '../utils/case.js';
import { parsePagination } from '../utils/pagination.js';

const router = Router();

const restaurantDto = (row) => {
  const r = rowToCamel(row);
  return {
    id: r.id,
    categoryId: r.categoryId,
    category: r.categoryId
      ? {
          id: r.categoryId,
          name: r.categoryName,
          emoji: r.categoryEmoji,
          sortOrder: r.categorySortOrder
        }
      : undefined,
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
  };
};

router.get('/', async (req, res, next) => {
  try {
    const { limit, offset } = parsePagination(req);

    const categoryId = z.string().uuid().optional().catch(undefined).parse(req.query.categoryId);
    const q = z.string().optional().catch(undefined).parse(req.query.q);

    const params = [];
    const where = ['r.is_active = true'];
    if (categoryId) {
      params.push(categoryId);
      where.push(`r.category_id = $${params.length}`);
    }
    if (q) {
      params.push(`%${q}%`);
      where.push(`r.name ILIKE $${params.length}`);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const countRes = await query(`SELECT COUNT(*)::int AS count FROM restaurants r ${whereSql}`, params);
    const total = countRes.rows[0]?.count ?? 0;

    params.push(limit);
    params.push(offset);

    const { rows } = await query(
      `SELECT r.id, r.category_id, r.name, r.description, r.price_range, r.rating, r.reviews_count,
              r.distance_miles, r.delivery_time_min, r.delivery_fee_cents, r.minimum_order_cents,
              r.cover_image_url, r.hero_image_url, r.is_active,
              rc.name AS category_name, rc.emoji AS category_emoji, rc.sort_order AS category_sort_order
       FROM restaurants r
       JOIN restaurant_categories rc ON rc.id = r.category_id
       ${whereSql}
       ORDER BY r.rating DESC, r.reviews_count DESC
       LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    const items = rows.map(restaurantDto);
    return listOk(res, items, { limit, offset, total });
  } catch (err) {
    return next(err);
  }
});

router.get('/:restaurantId', async (req, res, next) => {
  try {
    const restaurantId = z.string().uuid().parse(req.params.restaurantId);

    const { rows } = await query(
      `SELECT r.id, r.category_id, r.name, r.description, r.price_range, r.rating, r.reviews_count,
              r.distance_miles, r.delivery_time_min, r.delivery_fee_cents, r.minimum_order_cents,
              r.cover_image_url, r.hero_image_url, r.is_active,
              rc.name AS category_name, rc.emoji AS category_emoji, rc.sort_order AS category_sort_order
       FROM restaurants r
       JOIN restaurant_categories rc ON rc.id = r.category_id
       WHERE r.id = $1`,
      [restaurantId]
    );

    if (!rows.length) throw new ApiError('NOT_FOUND', 'Restaurant not found', 404);

    return ok(res, { restaurant: restaurantDto(rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.get('/:restaurantId/menu', async (req, res, next) => {
  try {
    const restaurantId = z.string().uuid().parse(req.params.restaurantId);

    const catsRes = await query(
      'SELECT id, restaurant_id, name, sort_order FROM menu_categories WHERE restaurant_id = $1 ORDER BY sort_order ASC, name ASC',
      [restaurantId]
    );
    const categories = rowsToCamel(catsRes.rows).map((c) => ({
      id: c.id,
      restaurantId: c.restaurantId,
      name: c.name,
      sortOrder: c.sortOrder
    }));

    const itemsRes = await query(
      `SELECT id, restaurant_id, menu_category_id, name, description, price_cents, image_url, unit_info, is_available
       FROM menu_items
       WHERE restaurant_id = $1
       ORDER BY created_at ASC`,
      [restaurantId]
    );

    const items = rowsToCamel(itemsRes.rows).map((i) => ({
      id: i.id,
      restaurantId: i.restaurantId,
      menuCategoryId: i.menuCategoryId ?? null,
      name: i.name,
      description: i.description ?? null,
      priceCents: i.priceCents,
      imageUrl: i.imageUrl ?? null,
      unitInfo: i.unitInfo ?? null,
      isAvailable: i.isAvailable,
      modifierGroups: []
    }));

    // modifier groups + options
    const itemIds = items.map((i) => i.id);
    if (itemIds.length) {
      const mgRes = await query(
        `SELECT id, menu_item_id, name, modifier_type, is_required, min_selected, max_selected, sort_order
         FROM modifier_groups
         WHERE menu_item_id = ANY($1::uuid[])
         ORDER BY sort_order ASC`,
        [itemIds]
      );
      const mgs = rowsToCamel(mgRes.rows);

      const mgIds = mgs.map((g) => g.id);
      const optRes = mgIds.length
        ? await query(
            `SELECT id, modifier_group_id, name, price_delta_cents, sort_order
             FROM modifier_options
             WHERE modifier_group_id = ANY($1::uuid[])
             ORDER BY sort_order ASC`,
            [mgIds]
          )
        : { rows: [] };
      const opts = rowsToCamel(optRes.rows);

      const optsByGroup = new Map();
      for (const o of opts) {
        if (!optsByGroup.has(o.modifierGroupId)) optsByGroup.set(o.modifierGroupId, []);
        optsByGroup.get(o.modifierGroupId).push({
          id: o.id,
          modifierGroupId: o.modifierGroupId,
          name: o.name,
          priceDeltaCents: o.priceDeltaCents,
          sortOrder: o.sortOrder
        });
      }

      const groupsByItem = new Map();
      for (const g of mgs) {
        if (!groupsByItem.has(g.menuItemId)) groupsByItem.set(g.menuItemId, []);
        groupsByItem.get(g.menuItemId).push({
          id: g.id,
          menuItemId: g.menuItemId,
          name: g.name,
          modifierType: g.modifierType,
          isRequired: g.isRequired,
          minSelected: g.minSelected,
          maxSelected: g.maxSelected,
          sortOrder: g.sortOrder,
          options: optsByGroup.get(g.id) || []
        });
      }

      for (const item of items) item.modifierGroups = groupsByItem.get(item.id) || [];
    }

    return ok(res, { categories, items });
  } catch (err) {
    return next(err);
  }
});

export default router;
