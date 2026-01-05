import { Router } from 'express';

import { query } from '../db.js';
import { requireAuth } from '../middleware/auth.js';
import { assert, validateUUID } from '../utils/validation.js';
import { errorResponse } from '../utils/response.js';

const router = Router();

function mapUser(u) {
  return {
    id: u.id,
    email: u.email,
    full_name: u.full_name,
    phone: u.phone,
    created_at: u.created_at
  };
}

router.patch('/users/me', requireAuth, async (req, res, next) => {
  try {
    const { full_name, phone } = req.body || {};
    assert(full_name !== undefined || phone !== undefined, 'Invalid input', null);

    const updates = [];
    const params = [];
    let idx = 1;

    if (full_name !== undefined) {
      assert(typeof full_name === 'string' && full_name.trim().length > 0, 'Invalid input', { field: 'full_name' });
      updates.push(`full_name = $${idx++}`);
      params.push(full_name);
    }

    if (phone !== undefined) {
      assert(phone === null || typeof phone === 'string', 'Invalid input', { field: 'phone' });
      updates.push(`phone = $${idx++}`);
      params.push(phone);
    }

    updates.push('updated_at = now()');

    params.push(req.user.id);

    const { rows } = await query(
      `UPDATE users SET ${updates.join(', ')}
       WHERE id = $${idx}
       RETURNING id, email, full_name, phone, created_at`,
      params
    );

    return res.json({ user: mapUser(rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.get('/users/me/payment-methods', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT id, brand, last4, exp_month, exp_year, billing_zip, created_at
       FROM payment_methods
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [req.user.id]
    );
    return res.json({ items: rows });
  } catch (err) {
    return next(err);
  }
});

router.post('/users/me/payment-methods', requireAuth, async (req, res, next) => {
  try {
    const { brand, last4, exp_month, exp_year, billing_zip } = req.body || {};
    assert(typeof brand === 'string' && brand.trim(), 'Invalid input', { field: 'brand' });
    assert(typeof last4 === 'string' && last4.length === 4, 'Invalid input', { field: 'last4' });
    assert(Number.isInteger(exp_month) && exp_month >= 1 && exp_month <= 12, 'Invalid input', { field: 'exp_month' });
    assert(Number.isInteger(exp_year) && exp_year >= 2020, 'Invalid input', { field: 'exp_year' });

    const { rows } = await query(
      `INSERT INTO payment_methods (user_id, brand, last4, exp_month, exp_year, billing_zip, token)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id, brand, last4, exp_month, exp_year, billing_zip, created_at`,
      [req.user.id, brand, last4, exp_month, exp_year, billing_zip ?? null, null]
    );

    return res.status(201).json({ payment_method: rows[0] });
  } catch (err) {
    return next(err);
  }
});

router.delete('/users/me/payment-methods/:payment_method_id', requireAuth, async (req, res, next) => {
  try {
    const { payment_method_id } = req.params;
    if (!validateUUID(payment_method_id)) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid input', { field: 'payment_method_id' });
    }

    await query('DELETE FROM payment_methods WHERE id = $1 AND user_id = $2', [payment_method_id, req.user.id]);
    return res.status(204).send();
  } catch (err) {
    return next(err);
  }
});

export default router;
