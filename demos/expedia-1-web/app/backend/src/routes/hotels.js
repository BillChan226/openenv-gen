const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');
const { applyQueryAliases } = require('../utils/queryAliases');

const router = express.Router();

function toHotel(row) {
  return {
    id: row.id,
    location_id: row.location_id,
    name: row.name,
    description: row.description,
    star_rating: row.star_rating,
    nightly_price: Number(row.nightly_price),
    amenities: row.amenities || [],
    address: row.address,
    lat: row.lat !== null ? Number(row.lat) : null,
    lng: row.lng !== null ? Number(row.lng) : null,
    photos: row.photos || [],
    vip_access: row.vip_access,
  };
}

router.get('/', async (req, res, next) => {
  try {
    const schema = z.object({
      location: z.string().uuid().optional(),
      q: z.string().optional(),
      min_price: z.coerce.number().optional(),
      max_price: z.coerce.number().optional(),
      min_stars: z.coerce.number().int().min(1).max(5).optional(),
      amenity: z.string().optional(),
      sort: z.enum(['price', 'stars', 'name']).default('price'),
      order: z.enum(['asc', 'desc']).default('asc'),
      page: z.coerce.number().int().min(1).default(1),
      limit: z.coerce.number().int().min(1).max(50).default(20),
    });

    // Support common UI/spec query param names.
    const aliasedQuery = applyQueryAliases(req.query, {
      location: ['location_id', 'locationId', 'city', 'city_id', 'cityId'],
      q: ['query', 'search', 'term'],
      min_price: ['minPrice', 'price_min', 'priceMin'],
      max_price: ['maxPrice', 'price_max', 'priceMax'],
      min_stars: ['minStars', 'stars', 'star_rating', 'starRating'],
      amenity: ['amenities', 'amenity[]'],
    });

    const parsed = schema.safeParse(aliasedQuery);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const { location, q, min_price, max_price, min_stars, amenity, sort, order, page, limit } = parsed.data;

    const where = [];
    const params = [];

    if (location) {
      params.push(location);
      where.push(`location_id = $${params.length}`);
    }
    if (q) {
      params.push(`%${q}%`);
      where.push(`name ILIKE $${params.length}`);
    }
    if (typeof min_price === 'number') {
      params.push(min_price);
      where.push(`nightly_price >= $${params.length}`);
    }
    if (typeof max_price === 'number') {
      params.push(max_price);
      where.push(`nightly_price <= $${params.length}`);
    }
    if (typeof min_stars === 'number') {
      params.push(min_stars);
      where.push(`star_rating >= $${params.length}`);
    }
    if (amenity) {
      params.push(amenity);
      where.push(`amenities @> ARRAY[$${params.length}]::text[]`);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const countResult = await db.query(`SELECT COUNT(*)::int AS count FROM hotels ${whereSql}`, params);
    const total = countResult.rows[0]?.count || 0;

    const sortCol = sort === 'price' ? 'nightly_price' : sort === 'stars' ? 'star_rating' : 'name';
    const orderSql = order.toUpperCase() === 'DESC' ? 'DESC' : 'ASC';

    const offset = (page - 1) * limit;
    const listParams = [...params, limit, offset];

    const result = await db.query(
      `SELECT id,location_id,name,description,star_rating,nightly_price,amenities,address,lat,lng,photos,vip_access
       FROM hotels
       ${whereSql}
       ORDER BY ${sortCol} ${orderSql}
       LIMIT $${listParams.length - 1} OFFSET $${listParams.length}`,
      listParams
    );

    return listResponse(res, result.rows.map(toHotel), total, page, limit);
  } catch (err) {
    return next(err);
  }
});

router.get('/:id', async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query(
      'SELECT id,location_id,name,description,star_rating,nightly_price,amenities,address,lat,lng,photos,vip_access FROM hotels WHERE id=$1',
      [id]
    );
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Hotel not found');
    return itemResponse(res, { hotel: toHotel(result.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.get('/:id/rooms', async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query(
      'SELECT id,hotel_id,name,description,bed_type,capacity,nightly_price,refundable FROM hotel_rooms WHERE hotel_id=$1 ORDER BY nightly_price ASC',
      [id]
    );
    const items = result.rows.map((r) => ({
      id: r.id,
      hotel_id: r.hotel_id,
      name: r.name,
      description: r.description,
      bed_type: r.bed_type,
      capacity: r.capacity,
      nightly_price: Number(r.nightly_price),
      refundable: r.refundable,
    }));
    return listResponse(res, items, result.rowCount, 1, result.rowCount);
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
