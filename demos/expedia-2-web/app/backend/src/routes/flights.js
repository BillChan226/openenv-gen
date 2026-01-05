import { Router } from 'express';

import { query } from '../db.js';
import { parseLimitOffset } from '../utils/pagination.js';
import { okList, okItem, errorResponse } from '../utils/response.js';

const router = Router();

function flightSelectSQL(whereSql, orderSql) {
  return `
    SELECT
      f.id,
      jsonb_build_object('id', a.id, 'code', a.code, 'name', a.name) AS airline,
      f.flight_number,
      jsonb_build_object('id', lo.id, 'code', lo.code, 'label', lo.label, 'type', lo.type, 'country_code', lo.country_code, 'region', lo.region, 'lat', lo.lat, 'lng', lo.lng) AS origin,
      jsonb_build_object('id', ld.id, 'code', ld.code, 'label', ld.label, 'type', ld.type, 'country_code', ld.country_code, 'region', ld.region, 'lat', ld.lat, 'lng', ld.lng) AS destination,
      f.depart_at,
      f.arrive_at,
      f.duration_minutes,
      f.stops,
      f.seat_class,
      f.price_cents,
      f.refundable,
      f.baggage_included
    FROM flights f
    JOIN airlines a ON a.id = f.airline_id
    JOIN locations lo ON lo.id = f.origin_location_id
    JOIN locations ld ON ld.id = f.destination_location_id
    ${whereSql}
    ${orderSql}
  `;
}

router.get('/flights', async (req, res, next) => {
  try {
    const { limit, offset } = parseLimitOffset(req);

    const origin = req.query.origin?.toString();
    const destination = req.query.destination?.toString();
    const depart_date = req.query.depart_date?.toString();
    const seat_class = (req.query.seat_class || 'economy').toString();
    const min_price_cents = req.query.min_price_cents ? Number(req.query.min_price_cents) : null;
    const max_price_cents = req.query.max_price_cents ? Number(req.query.max_price_cents) : null;
    const airline = req.query.airline?.toString();
    const stops = req.query.stops !== undefined ? Number(req.query.stops) : null;
    const sort = (req.query.sort || 'price').toString();

    const where = [];
    const params = [];
    let i = 1;

    if (origin) {
      where.push(`lo.code = $${i++}`);
      params.push(origin);
    }
    if (destination) {
      where.push(`ld.code = $${i++}`);
      params.push(destination);
    }
    if (depart_date) {
      where.push(`f.depart_at >= $${i++}::date AND f.depart_at < ($${i++}::date + interval '1 day')`);
      params.push(depart_date, depart_date);
    }
    if (seat_class) {
      where.push(`f.seat_class = $${i++}`);
      params.push(seat_class);
    }
    if (Number.isFinite(min_price_cents)) {
      where.push(`f.price_cents >= $${i++}`);
      params.push(min_price_cents);
    }
    if (Number.isFinite(max_price_cents)) {
      where.push(`f.price_cents <= $${i++}`);
      params.push(max_price_cents);
    }
    if (airline) {
      where.push(`a.code = $${i++}`);
      params.push(airline);
    }
    if (Number.isFinite(stops)) {
      where.push(`f.stops = $${i++}`);
      params.push(stops);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    let orderSql = 'ORDER BY f.price_cents ASC';
    if (sort === 'duration') orderSql = 'ORDER BY f.duration_minutes ASC';
    if (sort === 'departure_time') orderSql = 'ORDER BY f.depart_at ASC';

    const countRes = await query(
      `SELECT COUNT(*)::int AS count
       FROM flights f
       JOIN airlines a ON a.id = f.airline_id
       JOIN locations lo ON lo.id = f.origin_location_id
       JOIN locations ld ON ld.id = f.destination_location_id
       ${whereSql}`,
      params
    );

    const total = countRes.rows[0]?.count ?? 0;

    const dataParams = [...params, limit, offset];
    const rowsRes = await query(
      flightSelectSQL(whereSql, orderSql) + ` LIMIT $${i++} OFFSET $${i++}`,
      dataParams
    );

    return okList(res, { items: rowsRes.rows, total, limit, offset });
  } catch (err) {
    return next(err);
  }
});

router.get('/flights/:flight_id', async (req, res, next) => {
  try {
    const { flight_id } = req.params;

    const { rows } = await query(
      flightSelectSQL('WHERE f.id = $1', '') ,
      [flight_id]
    );

    const flight = rows[0];
    if (!flight) return errorResponse(res, 404, 'NOT_FOUND', 'Flight not found', null);

    return okItem(res, 'flight', flight);
  } catch (err) {
    return next(err);
  }
});

export default router;
