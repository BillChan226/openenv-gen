const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');
const { applyQueryAliases } = require('../utils/queryAliases');

const router = express.Router();

function toCar(row) {
  return {
    id: row.id,
    company: row.company,
    model: row.model,
    car_type: row.car_type,
    seats: row.seats,
    transmission: row.transmission,
    fuel_type: row.fuel_type,
    daily_price: Number(row.daily_price),
    location_id: row.location_id,
  };
}

router.get('/', async (req, res, next) => {
  try {
    const schema = z.object({
      location: z.string().uuid().optional(),
      company: z.string().optional(),
      car_type: z.string().optional(),
      max_price: z.coerce.number().optional(),
      sort: z.enum(['price', 'seats', 'company']).default('price'),
      order: z.enum(['asc', 'desc']).default('asc'),
      page: z.coerce.number().int().min(1).default(1),
      limit: z.coerce.number().int().min(1).max(50).default(20),
    });

    // Support common UI/spec query param names.
    const aliasedQuery = applyQueryAliases(req.query, {
      location: ['location_id', 'locationId', 'pickup', 'pickup_id', 'pickupId', 'city', 'city_id', 'cityId'],
      company: ['vendor', 'brand'],
      car_type: ['carType', 'type', 'vehicle_type', 'vehicleType'],
      max_price: ['maxPrice', 'price_max', 'priceMax'],
    });

    const parsed = schema.safeParse(aliasedQuery);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const { location, company, car_type, max_price, sort, order, page, limit } = parsed.data;

    const where = [];
    const params = [];

    if (location) {
      params.push(location);
      where.push(`location_id = $${params.length}`);
    }
    if (company) {
      params.push(company);
      where.push(`company ILIKE $${params.length}`);
    }
    if (car_type) {
      params.push(car_type);
      where.push(`car_type ILIKE $${params.length}`);
    }
    if (typeof max_price === 'number') {
      params.push(max_price);
      where.push(`daily_price <= $${params.length}`);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const countResult = await db.query(`SELECT COUNT(*)::int AS count FROM cars ${whereSql}`, params);
    const total = countResult.rows[0]?.count || 0;

    const sortCol = sort === 'price' ? 'daily_price' : sort;
    const orderSql = order.toUpperCase() === 'DESC' ? 'DESC' : 'ASC';

    const offset = (page - 1) * limit;
    const listParams = [...params, limit, offset];

    const result = await db.query(
      `SELECT id,company,model,car_type,seats,transmission,fuel_type,daily_price,location_id
       FROM cars
       ${whereSql}
       ORDER BY ${sortCol} ${orderSql}
       LIMIT $${listParams.length - 1} OFFSET $${listParams.length}`,
      listParams
    );

    return listResponse(res, result.rows.map(toCar), total, page, limit);
  } catch (err) {
    return next(err);
  }
});

router.get('/:id', async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query(
      'SELECT id,company,model,car_type,seats,transmission,fuel_type,daily_price,location_id FROM cars WHERE id=$1',
      [id]
    );
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Car not found');
    return itemResponse(res, { car: toCar(result.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
