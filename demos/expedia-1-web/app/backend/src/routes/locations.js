const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { listResponse, errorResponse } = require('../utils/responses');

const router = express.Router();

function toLocation(row) {
  return {
    id: row.id,
    type: row.type,
    code: row.code,
    name: row.name,
    country: row.country,
    region: row.region,
    lat: row.lat !== null ? Number(row.lat) : null,
    lng: row.lng !== null ? Number(row.lng) : null,
  };
}

router.get('/', async (req, res, next) => {
  try {
    const schema = z.object({
      // q is optional: when omitted, return a default list (e.g., popular/seeded locations)
      // This keeps GET /api/locations returning 200 with a list response.
      // If provided, allow 1+ chars to avoid 400s for short queries.
      q: z.string().min(1).optional(),
      type: z.enum(['airport', 'city', 'region', 'place']).optional(),
      limit: z.coerce.number().int().min(1).max(50).default(8),
    });

    const parsed = schema.safeParse(req.query);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const { q, type, limit } = parsed.data;

    const where = [];
    const params = [];

    if (q) {
      params.push(`%${q}%`);
      where.push(`(name ILIKE $${params.length} OR code ILIKE $${params.length})`);
    }

    if (type) {
      params.push(type);
      where.push(`type = $${params.length}`);
    }

    params.push(limit);

    const sql = `
      SELECT id,type,code,name,country,region,lat,lng
      FROM locations
      ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
      ORDER BY
        ${q ? 'CASE WHEN code ILIKE $1 THEN 0 ELSE 1 END,' : ''}
        name ASC
      LIMIT $${params.length}
    `;

    const result = await db.query(sql, params);
    return listResponse(res, result.rows.map(toLocation), result.rowCount, 1, limit);
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
