import { Router } from 'express';

import { query } from '../db.js';
import { parseLimitOffset } from '../utils/pagination.js';
import { okList, okItem, errorResponse } from '../utils/response.js';

const router = Router();

function carSelect(whereSql, orderSql) {
  return `
    SELECT
      c.id,
      jsonb_build_object('id', cc.id, 'name', cc.name) AS company,
      jsonb_build_object('id', lp.id, 'code', lp.code, 'label', lp.label, 'type', lp.type, 'country_code', lp.country_code, 'region', lp.region, 'lat', lp.lat, 'lng', lp.lng) AS pickup_location,
      jsonb_build_object('id', ld.id, 'code', ld.code, 'label', ld.label, 'type', ld.type, 'country_code', ld.country_code, 'region', ld.region, 'lat', ld.lat, 'lng', ld.lng) AS dropoff_location,
      c.model,
      c.car_type,
      c.seats,
      c.transmission,
      c.fuel_type,
      c.base_price_per_day_cents
    FROM cars c
    JOIN car_companies cc ON cc.id = c.company_id
    JOIN locations lp ON lp.id = c.pickup_location_id
    JOIN locations ld ON ld.id = c.dropoff_location_id
    ${whereSql}
    ${orderSql}
  `;
}

router.get('/cars', async (req, res, next) => {
  try {
    const { limit, offset } = parseLimitOffset(req);

    const pickup_location = req.query.pickup_location?.toString();
    const dropoff_location = req.query.dropoff_location?.toString();
    const car_type = req.query.car_type?.toString();
    const company = req.query.company?.toString();
    const min_price_cents = req.query.min_price_cents ? Number(req.query.min_price_cents) : null;
    const max_price_cents = req.query.max_price_cents ? Number(req.query.max_price_cents) : null;
    const sort = (req.query.sort || 'price').toString();

    const where = [];
    const params = [];
    let i = 1;

    if (pickup_location) {
      where.push(`lp.code = $${i++}`);
      params.push(pickup_location);
    }
    if (dropoff_location) {
      where.push(`ld.code = $${i++}`);
      params.push(dropoff_location);
    }
    if (car_type) {
      where.push(`c.car_type = $${i++}`);
      params.push(car_type);
    }
    if (company) {
      where.push(`cc.name ILIKE $${i++}`);
      params.push(company);
    }
    if (Number.isFinite(min_price_cents)) {
      where.push(`c.base_price_per_day_cents >= $${i++}`);
      params.push(min_price_cents);
    }
    if (Number.isFinite(max_price_cents)) {
      where.push(`c.base_price_per_day_cents <= $${i++}`);
      params.push(max_price_cents);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    let orderSql = 'ORDER BY c.base_price_per_day_cents ASC';
    if (sort === 'seats') orderSql = 'ORDER BY c.seats DESC';

    const countRes = await query(
      `SELECT COUNT(*)::int AS count
       FROM cars c
       JOIN car_companies cc ON cc.id = c.company_id
       JOIN locations lp ON lp.id = c.pickup_location_id
       JOIN locations ld ON ld.id = c.dropoff_location_id
       ${whereSql}`,
      params
    );
    const total = countRes.rows[0]?.count ?? 0;

    const dataParams = [...params, limit, offset];
    const rowsRes = await query(carSelect(whereSql, orderSql) + ` LIMIT $${i++} OFFSET $${i++}`, dataParams);

    return okList(res, { items: rowsRes.rows, total, limit, offset });
  } catch (err) {
    return next(err);
  }
});

router.get('/cars/:car_id', async (req, res, next) => {
  try {
    const { car_id } = req.params;

    const { rows } = await query(carSelect('WHERE c.id = $1', ''), [car_id]);
    const car = rows[0];
    if (!car) return errorResponse(res, 404, 'NOT_FOUND', 'Car not found', null);

    return okItem(res, 'car', car);
  } catch (err) {
    return next(err);
  }
});

export default router;
