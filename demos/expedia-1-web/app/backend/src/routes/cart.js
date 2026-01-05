const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { requireAuth } = require('../middleware/auth');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');

const router = express.Router();

function toCartItem(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    item_type: row.item_type,
    ref_id: row.ref_id,
    start_date: row.start_date,
    end_date: row.end_date,
    quantity: row.quantity,
    meta: row.meta,
    created_at: row.created_at,
  };
}

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const result = await db.query(
      'SELECT id,user_id,item_type,ref_id,start_date,end_date,quantity,meta,created_at FROM cart_items WHERE user_id=$1 ORDER BY created_at DESC',
      [req.user.id]
    );
    return listResponse(res, result.rows.map(toCartItem), result.rowCount, 1, result.rowCount);
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const schema = z.object({
      item_type: z.enum(['flight', 'hotel', 'car']),
      ref_id: z.string().uuid(),
      start_date: z.string().optional().nullable(),
      end_date: z.string().optional().nullable(),
      quantity: z.number().int().min(1).max(9).default(1),
      meta: z.record(z.any()).optional().default({}),
    });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid request body', parsed.error.flatten());
    }

    const { item_type, ref_id, start_date, end_date, quantity, meta } = parsed.data;

    const inserted = await db.query(
      `INSERT INTO cart_items (user_id, item_type, ref_id, start_date, end_date, quantity, meta)
       VALUES ($1,$2,$3,$4,$5,$6,$7)
       RETURNING id,user_id,item_type,ref_id,start_date,end_date,quantity,meta,created_at`,
      [req.user.id, item_type, ref_id, start_date || null, end_date || null, quantity, meta]
    );

    return itemResponse(res, { cart_item: toCartItem(inserted.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query('DELETE FROM cart_items WHERE id=$1 AND user_id=$2', [id, req.user.id]);
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Cart item not found');
    return itemResponse(res, { success: true });
  } catch (err) {
    return next(err);
  }
});

router.delete('/', requireAuth, async (req, res, next) => {
  try {
    await db.query('DELETE FROM cart_items WHERE user_id=$1', [req.user.id]);
    return itemResponse(res, { success: true });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
