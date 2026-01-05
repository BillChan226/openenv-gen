import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, listOk, ok } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

const paymentSchema = z.object({
  brand: z.enum(['VISA', 'MASTERCARD', 'AMEX', 'DISCOVER', 'OTHER']),
  last4: z.string().min(4).max(4),
  expMonth: z.number().int().min(1).max(12),
  expYear: z.number().int().min(2020),
  billingZip: z.string().optional(),
  isDefault: z.boolean().optional()
});

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT id, user_id, brand, last4, exp_month, exp_year, billing_zip, is_default, created_at
       FROM payment_methods
       WHERE user_id = $1
       ORDER BY is_default DESC, created_at DESC`,
      [req.user.id]
    );

    const items = rowsToCamel(rows).map((p) => ({
      id: p.id,
      userId: p.userId,
      brand: p.brand,
      last4: p.last4,
      expMonth: p.expMonth,
      expYear: p.expYear,
      billingZip: p.billingZip ?? null,
      isDefault: p.isDefault,
      createdAt: p.createdAt
    }));

    return listOk(res, items, { limit: items.length, offset: 0, total: items.length });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const body = paymentSchema.parse(req.body);

    if (body.isDefault) {
      await query('UPDATE payment_methods SET is_default = false WHERE user_id = $1', [req.user.id]);
    }

    const { rows } = await query(
      `INSERT INTO payment_methods (user_id, brand, last4, exp_month, exp_year, billing_zip, is_default)
       VALUES ($1,$2,$3,$4,$5,$6,$7)
       RETURNING id, user_id, brand, last4, exp_month, exp_year, billing_zip, is_default, created_at`,
      [
        req.user.id,
        body.brand,
        body.last4,
        body.expMonth,
        body.expYear,
        body.billingZip ?? null,
        body.isDefault ?? false
      ]
    );

    const p = rowsToCamel(rows)[0];
    return ok(res, {
      paymentMethod: {
        id: p.id,
        userId: p.userId,
        brand: p.brand,
        last4: p.last4,
        expMonth: p.expMonth,
        expYear: p.expYear,
        billingZip: p.billingZip ?? null,
        isDefault: p.isDefault,
        createdAt: p.createdAt
      }
    });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:paymentMethodId', requireAuth, async (req, res, next) => {
  try {
    const paymentMethodId = z.string().uuid().parse(req.params.paymentMethodId);

    const del = await query('DELETE FROM payment_methods WHERE id = $1 AND user_id = $2', [
      paymentMethodId,
      req.user.id
    ]);
    if (!del.rowCount) throw new ApiError('NOT_FOUND', 'Payment method not found', 404);

    return ok(res, { deleted: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
