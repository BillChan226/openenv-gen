const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { requireAuth } = require('../middleware/auth');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');

const router = express.Router();

function toBooking(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    booking_type: row.booking_type,
    status: row.status,
    total_amount: Number(row.total_amount),
    currency: row.currency,
    details: row.details,
    created_at: row.created_at,
  };
}

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const schema = z.object({
      status: z.enum(['confirmed', 'cancelled']).optional(),
      page: z.coerce.number().int().min(1).default(1),
      limit: z.coerce.number().int().min(1).max(50).default(20),
    });

    const parsed = schema.safeParse(req.query);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const { status, page, limit } = parsed.data;

    const where = ['user_id=$1'];
    const params = [req.user.id];

    if (status) {
      params.push(status);
      where.push(`status=$${params.length}`);
    }

    const whereSql = `WHERE ${where.join(' AND ')}`;

    const countResult = await db.query(`SELECT COUNT(*)::int AS count FROM bookings ${whereSql}`, params);
    const total = countResult.rows[0]?.count || 0;

    const offset = (page - 1) * limit;
    const listParams = [...params, limit, offset];

    const result = await db.query(
      `SELECT id,user_id,booking_type,status,total_amount,currency,details,created_at
       FROM bookings
       ${whereSql}
       ORDER BY created_at DESC
       LIMIT $${listParams.length - 1} OFFSET $${listParams.length}`,
      listParams
    );

    return listResponse(res, result.rows.map(toBooking), total, page, limit);
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const schema = z.object({
      booking_type: z.enum(['flight', 'hotel', 'car', 'package']),
      total_amount: z.number().nonnegative(),
      currency: z.string().default('USD'),
      details: z.record(z.any()).default({}),
    });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid request body', parsed.error.flatten());
    }

    const { booking_type, total_amount, currency, details } = parsed.data;

    const inserted = await db.query(
      `INSERT INTO bookings (user_id, booking_type, status, total_amount, currency, details)
       VALUES ($1,$2,'confirmed',$3,$4,$5)
       RETURNING id,user_id,booking_type,status,total_amount,currency,details,created_at`,
      [req.user.id, booking_type, total_amount, currency, details]
    );

    // clear cart on booking
    await db.query('DELETE FROM cart_items WHERE user_id=$1', [req.user.id]);

    return itemResponse(res, { booking: toBooking(inserted.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.post('/:id/cancel', requireAuth, async (req, res, next) => {
  try {
    const id = req.params.id;

    const updated = await db.query(
      `UPDATE bookings
       SET status='cancelled'
       WHERE id=$1 AND user_id=$2 AND status<>'cancelled'
       RETURNING id,user_id,booking_type,status,total_amount,currency,details,created_at`,
      [id, req.user.id]
    );

    if (updated.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Booking not found');

    return itemResponse(res, { booking: toBooking(updated.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.get('/:id/confirmation', requireAuth, async (req, res, next) => {
  try {
    const schema = z.object({
      format: z.enum(['json', 'text']).default('json'),
    });
    const parsed = schema.safeParse(req.query);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid query params', parsed.error.flatten());
    }

    const id = req.params.id;
    const result = await db.query(
      'SELECT id,user_id,booking_type,status,total_amount,currency,details,created_at FROM bookings WHERE id=$1 AND user_id=$2',
      [id, req.user.id]
    );
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Booking not found');

    const booking = toBooking(result.rows[0]);

    if (parsed.data.format === 'text') {
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      return res.send(
        `Booking ${booking.id}\nType: ${booking.booking_type}\nStatus: ${booking.status}\nTotal: ${booking.total_amount} ${booking.currency}\nCreated: ${booking.created_at}\n`
      );
    }

    return itemResponse(res, { booking });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
