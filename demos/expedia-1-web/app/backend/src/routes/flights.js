const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');
const { applyQueryAliases } = require('../utils/queryAliases');

const router = express.Router();

function toFlight(row) {
  return {
    id: row.id,
    origin_location_id: row.origin_location_id,
    destination_location_id: row.destination_location_id,
    airline: row.airline,
    flight_number: row.flight_number,
    depart_time: row.depart_time,
    arrive_time: row.arrive_time,
    duration_minutes: row.duration_minutes,
    stops: row.stops,
    base_price: Number(row.base_price),
    cabin_class: row.cabin_class,
  };
}

router.get('/', async (req, res, next) => {
  try {
    const schema = z.object({
      origin: z.string().uuid().optional(),
      destination: z.string().uuid().optional(),
      depart_date: z.string().optional(),
      passengers: z.coerce.number().int().min(1).max(9).default(1),
      cabin_class: z.enum(['Economy', 'Business', 'First']).optional(),
      max_stops: z.coerce.number().int().min(0).max(3).optional(),
      airline: z.string().optional(),
      sort: z.enum(['price', 'duration', 'depart_time']).default('price'),
      order: z.enum(['asc', 'desc']).default('asc'),
      page: z.coerce.number().int().min(1).default(1),
      limit: z.coerce.number().int().min(1).max(50).default(20),
    });

    // Support common UI/spec query param names.
    const aliasedQuery = applyQueryAliases(req.query, {
      origin: ['origin_id', 'originId', 'from', 'from_id', 'fromId'],
      destination: ['destination_id', 'destinationId', 'to', 'to_id', 'toId'],
      depart_date: ['departDate', 'departure_date', 'departureDate', 'date'],
      passengers: ['adults', 'travelerCount', 'travellers', 'travelers'],
      cabin_class: ['cabinClass', 'cabin'],
      max_stops: ['maxStops', 'stops'],
    });

    const parsed = schema.safeParse(aliasedQuery);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const {
      origin,
      destination,
      depart_date,
      passengers,
      cabin_class,
      max_stops,
      airline,
      sort,
      order,
      page,
      limit,
    } = parsed.data;

    const where = [];
    const params = [];

    if (origin) {
      params.push(origin);
      where.push(`origin_location_id = $${params.length}`);
    }
    if (destination) {
      params.push(destination);
      where.push(`destination_location_id = $${params.length}`);
    }
    if (depart_date) {
      params.push(depart_date);
      where.push(`depart_time::date = $${params.length}::date`);
    }
    if (cabin_class) {
      params.push(cabin_class);
      where.push(`cabin_class = $${params.length}`);
    }
    if (typeof max_stops === 'number') {
      params.push(max_stops);
      where.push(`stops <= $${params.length}`);
    }
    if (airline) {
      params.push(airline);
      where.push(`airline ILIKE $${params.length}`);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const countSql = `SELECT COUNT(*)::int AS count FROM flights ${whereSql}`;
    const countResult = await db.query(countSql, params);
    const total = countResult.rows[0]?.count || 0;

    // Map API sort keys to actual DB columns.
    // NOTE: DB column is `base_price`, but API exposes `price`.
    const sortCol =
      sort === 'duration'
        ? 'duration_minutes'
        : sort === 'price'
          ? 'base_price'
          : sort;

    const orderSql = order.toUpperCase() === 'DESC' ? 'DESC' : 'ASC';

    const offset = (page - 1) * limit;
    const listParams = [...params, limit, offset];

    const listSql = `
      SELECT id,origin_location_id,destination_location_id,airline,flight_number,depart_time,arrive_time,duration_minutes,stops,base_price,cabin_class
      FROM flights
      ${whereSql}
      ORDER BY ${sortCol} ${orderSql}
      LIMIT $${listParams.length - 1} OFFSET $${listParams.length}
    `;

    const result = await db.query(listSql, listParams);

    // Simple pricing multiplier by passengers
    const items = result.rows.map((r) => {
      const f = toFlight(r);
      return {
        ...f,
        total_price: Number((f.base_price * passengers).toFixed(2)),
        passengers,
      };
    });

    return listResponse(res, items, total, page, limit);
  } catch (err) {
    return next(err);
  }
});

router.get('/:id', async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query(
      'SELECT id,origin_location_id,destination_location_id,airline,flight_number,depart_time,arrive_time,duration_minutes,stops,base_price,cabin_class FROM flights WHERE id=$1',
      [id]
    );
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Flight not found');
    return itemResponse(res, { flight: toFlight(result.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
