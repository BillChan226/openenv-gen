const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { requireAuth } = require('../middleware/auth');
const { listResponse, itemResponse, errorResponse } = require('../utils/responses');

const router = express.Router();

function toPaymentMethod(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    brand: row.brand,
    last4: row.last4,
    exp_month: row.exp_month,
    exp_year: row.exp_year,
    token: row.token,
    billing_name: row.billing_name,
    created_at: row.created_at,
  };
}

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const result = await db.query(
      'SELECT id,user_id,brand,last4,exp_month,exp_year,token,billing_name,created_at FROM payment_methods WHERE user_id=$1 ORDER BY created_at DESC',
      [req.user.id]
    );
    return listResponse(res, result.rows.map(toPaymentMethod), result.rowCount, 1, result.rowCount);
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const schema = z.object({
      brand: z.string().min(1),
      last4: z.string().regex(/^\d{4}$/),
      exp_month: z.number().int().min(1).max(12),
      exp_year: z.number().int().min(2000),
      token: z.string().min(1),
      billing_name: z.string().nullable().optional(),
    });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid request body', parsed.error.flatten());
    }

    const { brand, last4, exp_month, exp_year, token, billing_name } = parsed.data;

    const inserted = await db.query(
      `INSERT INTO payment_methods (user_id, brand, last4, exp_month, exp_year, token, billing_name)
       VALUES ($1,$2,$3,$4,$5,$6,$7)
       RETURNING id,user_id,brand,last4,exp_month,exp_year,token,billing_name,created_at`,
      [req.user.id, brand, last4, exp_month, exp_year, token, billing_name || null]
    );

    return itemResponse(res, { payment_method: toPaymentMethod(inserted.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    const id = req.params.id;
    const result = await db.query('DELETE FROM payment_methods WHERE id=$1 AND user_id=$2', [id, req.user.id]);
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'Payment method not found');
    return itemResponse(res, { success: true });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
