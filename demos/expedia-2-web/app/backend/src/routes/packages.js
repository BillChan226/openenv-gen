import { Router } from 'express';

import { query } from '../db.js';
import { parseLimitOffset } from '../utils/pagination.js';
import { okList, okItem, errorResponse } from '../utils/response.js';

const router = Router();

function packageSelect(whereSql, orderSql) {
  return `
    SELECT
      p.id,
      p.bundle_type,
      p.discount_cents,
      p.created_at,
      jsonb_build_object(
        'id', f.id,
        'flight_number', f.flight_number,
        'depart_at', f.depart_at,
        'arrive_at', f.arrive_at,
        'duration_minutes', f.duration_minutes,
        'stops', f.stops,
        'seat_class', f.seat_class,
        'price_cents', f.price_cents,
        'refundable', f.refundable,
        'baggage_included', f.baggage_included
      ) AS flight,
      jsonb_build_object(
        'id', h.id,
        'name', h.name,
        'star_rating', h.star_rating,
        'review_rating', h.review_rating,
        'review_count', h.review_count,
        'nightly_base_price_cents', h.nightly_base_price_cents,
        'lat', h.lat,
        'lng', h.lng
      ) AS hotel,
      CASE WHEN c.id IS NULL THEN NULL ELSE jsonb_build_object(
        'id', c.id,
        'model', c.model,
        'car_type', c.car_type,
        'seats', c.seats,
        'transmission', c.transmission,
        'fuel_type', c.fuel_type,
        'base_price_per_day_cents', c.base_price_per_day_cents
      ) END AS car
    FROM packages p
    JOIN flights f ON f.id = p.flight_id
    JOIN hotels h ON h.id = p.hotel_id
    LEFT JOIN cars c ON c.id = p.car_id
    ${whereSql}
    ${orderSql}
  `;
}

router.get('/packages', async (req, res, next) => {
  try {
    const { limit, offset } = parseLimitOffset(req);

    const bundle_type = req.query.bundle_type?.toString();
    const sort = (req.query.sort || 'discount').toString();

    const where = [];
    const params = [];
    let i = 1;

    if (bundle_type) {
      where.push(`p.bundle_type = $${i++}`);
      params.push(bundle_type);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    let orderSql = 'ORDER BY p.discount_cents DESC';
    if (sort === 'newest') orderSql = 'ORDER BY p.created_at DESC';

    const countRes = await query(`SELECT COUNT(*)::int AS count FROM packages p ${whereSql}`, params);
    const total = countRes.rows[0]?.count ?? 0;

    const dataParams = [...params, limit, offset];
    const rowsRes = await query(packageSelect(whereSql, orderSql) + ` LIMIT $${i++} OFFSET $${i++}`, dataParams);

    return okList(res, { items: rowsRes.rows, total, limit, offset });
  } catch (err) {
    return next(err);
  }
});

router.get('/packages/:package_id', async (req, res, next) => {
  try {
    const { package_id } = req.params;

    const { rows } = await query(packageSelect('WHERE p.id = $1', ''), [package_id]);
    const pkg = rows[0];
    if (!pkg) return errorResponse(res, 404, 'NOT_FOUND', 'Package not found', null);

    return okItem(res, 'package', pkg);
  } catch (err) {
    return next(err);
  }
});

export default router;
