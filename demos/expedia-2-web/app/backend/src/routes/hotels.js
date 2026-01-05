import { Router } from 'express';

import { query } from '../db.js';
import { parseLimitOffset } from '../utils/pagination.js';
import { okList, errorResponse } from '../utils/response.js';

const router = Router();

function hotelBaseSelect(whereSql, orderSql) {
  return `
    SELECT
      h.id,
      h.name,
      h.description,
      h.address,
      jsonb_build_object('id', l.id, 'code', l.code, 'label', l.label, 'type', l.type, 'country_code', l.country_code, 'region', l.region, 'lat', l.lat, 'lng', l.lng) AS location,
      h.star_rating,
      h.review_rating,
      h.review_count,
      h.nightly_base_price_cents,
      h.is_vip_access,
      h.lat,
      h.lng,
      COALESCE(
        (SELECT jsonb_agg(jsonb_build_object('url', hp.url, 'sort_order', hp.sort_order) ORDER BY hp.sort_order ASC)
         FROM hotel_photos hp WHERE hp.hotel_id = h.id),
        '[]'::jsonb
      ) AS photos,
      COALESCE(
        (SELECT jsonb_agg(jsonb_build_object('code', ha.code, 'label', ha.label) ORDER BY ha.label ASC)
         FROM hotel_hotel_amenities hha
         JOIN hotel_amenities ha ON ha.id = hha.amenity_id
         WHERE hha.hotel_id = h.id),
        '[]'::jsonb
      ) AS amenities
    FROM hotels h
    JOIN locations l ON l.id = h.location_id
    ${whereSql}
    ${orderSql}
  `;
}

router.get('/hotels', async (req, res, next) => {
  try {
    const { limit, offset } = parseLimitOffset(req);

    const location = req.query.location?.toString();
    const min_price_cents = req.query.min_price_cents ? Number(req.query.min_price_cents) : null;
    const max_price_cents = req.query.max_price_cents ? Number(req.query.max_price_cents) : null;
    const star_rating = req.query.star_rating !== undefined ? Number(req.query.star_rating) : null;
    const amenities = req.query.amenities?.toString();
    const sort = (req.query.sort || 'price').toString();

    const where = [];
    const params = [];
    let i = 1;

    if (location) {
      where.push(`l.code = $${i++}`);
      params.push(location);
    }
    if (Number.isFinite(min_price_cents)) {
      where.push(`h.nightly_base_price_cents >= $${i++}`);
      params.push(min_price_cents);
    }
    if (Number.isFinite(max_price_cents)) {
      where.push(`h.nightly_base_price_cents <= $${i++}`);
      params.push(max_price_cents);
    }
    if (Number.isFinite(star_rating)) {
      where.push(`h.star_rating >= $${i++}`);
      params.push(star_rating);
    }

    if (amenities) {
      const codes = amenities
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      if (codes.length) {
        where.push(`EXISTS (
          SELECT 1
          FROM hotel_hotel_amenities hha
          JOIN hotel_amenities ha ON ha.id = hha.amenity_id
          WHERE hha.hotel_id = h.id AND ha.code = ANY($${i++})
        )`);
        params.push(codes);
      }
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    let orderSql = 'ORDER BY h.nightly_base_price_cents ASC';
    if (sort === 'rating') orderSql = 'ORDER BY h.review_rating DESC NULLS LAST';
    if (sort === 'distance') orderSql = 'ORDER BY h.id ASC';

    const countRes = await query(
      `SELECT COUNT(*)::int AS count
       FROM hotels h
       JOIN locations l ON l.id = h.location_id
       ${whereSql}`,
      params
    );
    const total = countRes.rows[0]?.count ?? 0;

    const dataParams = [...params, limit, offset];
    const rowsRes = await query(
      hotelBaseSelect(whereSql, orderSql) + ` LIMIT $${i++} OFFSET $${i++}`,
      dataParams
    );

    return okList(res, { items: rowsRes.rows, total, limit, offset });
  } catch (err) {
    return next(err);
  }
});

router.get('/hotels/:hotel_id', async (req, res, next) => {
  try {
    const { hotel_id } = req.params;

    const hotelRes = await query(hotelBaseSelect('WHERE h.id = $1', ''), [hotel_id]);
    const hotel = hotelRes.rows[0];
    if (!hotel) return errorResponse(res, 404, 'NOT_FOUND', 'Hotel not found', null);

    const roomsRes = await query(
      `SELECT id, hotel_id, name, bed_configuration, max_guests, price_per_night_cents, inventory
       FROM hotel_rooms
       WHERE hotel_id = $1
       ORDER BY price_per_night_cents ASC`,
      [hotel_id]
    );

    return res.json({ hotel, rooms: roomsRes.rows });
  } catch (err) {
    return next(err);
  }
});

export default router;
