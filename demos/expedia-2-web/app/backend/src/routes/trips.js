import { Router } from 'express';

import { query, withTransaction } from '../db.js';
import { requireAuth } from '../middleware/auth.js';
import { assert } from '../utils/validation.js';
import { parseLimitOffset } from '../utils/pagination.js';
import { okList, okItem, errorResponse } from '../utils/response.js';

const router = Router();

router.get('/trips', requireAuth, async (req, res, next) => {
  try {
    const { limit, offset } = parseLimitOffset(req);

    const countRes = await query('SELECT COUNT(*)::int AS count FROM orders WHERE user_id = $1', [req.user.id]);
    const total = countRes.rows[0]?.count ?? 0;

    const { rows } = await query(
      `SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,
              payment_status, refund_total_cents, cancelled_at, confirmation_code, created_at
       FROM orders
       WHERE user_id = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [req.user.id, limit, offset]
    );

    return okList(res, { items: rows, total, limit, offset });
  } catch (err) {
    return next(err);
  }
});

router.get('/trips/:order_id', requireAuth, async (req, res, next) => {
  try {
    const { order_id } = req.params;

    const orderRes = await query(
      `SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,
              payment_status, refund_total_cents, cancelled_at, confirmation_code, created_at
       FROM orders
       WHERE id = $1 AND user_id = $2`,
      [order_id, req.user.id]
    );

    const order = orderRes.rows[0];
    if (!order) return errorResponse(res, 404, 'NOT_FOUND', 'Trip not found', null);

    const itemsRes = await query(
      `SELECT id, order_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
              start_date, end_date, passengers, guests, rooms, extras,
              subtotal_cents, taxes_cents, fees_cents, total_cents,
              status, cancelled_at, created_at
       FROM order_items
       WHERE order_id = $1
       ORDER BY created_at ASC`,
      [order_id]
    );

    return okItem(res, 'trip', { order, items: itemsRes.rows });
  } catch (err) {
    return next(err);
  }
});

router.post('/trips/:order_id/cancel', requireAuth, async (req, res, next) => {
  try {
    const { order_id } = req.params;

    const cancelled = await withTransaction(async (client) => {
      const oRes = await client.query(
        `SELECT id, status, total_cents
         FROM orders
         WHERE id = $1 AND user_id = $2
         FOR UPDATE`,
        [order_id, req.user.id]
      );
      const order = oRes.rows[0];
      if (!order) return null;
      if (order.status === 'cancelled') return { already: true, order_id: order.id };

      await client.query(
        `UPDATE orders
         SET status = 'cancelled', cancelled_at = now(), refund_total_cents = total_cents
         WHERE id = $1`,
        [order.id]
      );

      await client.query(
        `UPDATE order_items
         SET status = 'cancelled', cancelled_at = now()
         WHERE order_id = $1`,
        [order.id]
      );

      const updated = await client.query(
        `SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,
                payment_status, refund_total_cents, cancelled_at, confirmation_code, created_at
         FROM orders
         WHERE id = $1`,
        [order.id]
      );

      return { order: updated.rows[0] };
    });

    if (!cancelled) return errorResponse(res, 404, 'NOT_FOUND', 'Trip not found', null);

    return res.json(cancelled);
  } catch (err) {
    return next(err);
  }
});

router.patch('/trips/:order_id/items/:order_item_id', requireAuth, async (req, res, next) => {
  try {
    const { order_id, order_item_id } = req.params;
    const { start_date, end_date, passengers, guests, rooms, extras } = req.body || {};

    assert(start_date || end_date || passengers || guests || rooms || extras, 'Invalid input', null);

    const orderRes = await query('SELECT id FROM orders WHERE id = $1 AND user_id = $2', [order_id, req.user.id]);
    if (!orderRes.rows[0]) return errorResponse(res, 404, 'NOT_FOUND', 'Trip not found', null);

    const existingRes = await query(
      `SELECT * FROM order_items WHERE id = $1 AND order_id = $2`,
      [order_item_id, order_id]
    );
    const item = existingRes.rows[0];
    if (!item) return errorResponse(res, 404, 'NOT_FOUND', 'Trip item not found', null);
    if (item.status === 'cancelled') return errorResponse(res, 400, 'VALIDATION_ERROR', 'Cannot modify cancelled item', null);

    const updatedRes = await query(
      `UPDATE order_items
       SET start_date = COALESCE($1, start_date),
           end_date = COALESCE($2, end_date),
           passengers = COALESCE($3, passengers),
           guests = COALESCE($4, guests),
           rooms = COALESCE($5, rooms),
           extras = COALESCE($6, extras),
           status = 'modified'
       WHERE id = $7 AND order_id = $8
       RETURNING id, order_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
                 start_date, end_date, passengers, guests, rooms, extras,
                 subtotal_cents, taxes_cents, fees_cents, total_cents,
                 status, cancelled_at, created_at`,
      [start_date ?? null, end_date ?? null, passengers ?? null, guests ?? null, rooms ?? null, extras ?? null, order_item_id, order_id]
    );

    return res.json({ order_item: updatedRes.rows[0] });
  } catch (err) {
    return next(err);
  }
});

export default router;
