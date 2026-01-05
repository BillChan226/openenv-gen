import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, ok } from '../utils/response.js';
import { rowToCamel } from '../utils/case.js';

const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const code = z.string().min(1).transform((s) => s.trim().toUpperCase()).parse(req.query.code);

    const { rows } = await query(
      `SELECT id, code, description, discount_type, discount_value, min_subtotal_cents, max_discount_cents, is_active
       FROM promo_codes
       WHERE code = $1`,
      [code]
    );

    if (!rows.length) throw new ApiError('NOT_FOUND', 'Promo code not found', 404);

    const p = rowToCamel(rows[0]);
    return ok(res, {
      promoCode: {
        id: p.id,
        code: p.code,
        description: p.description ?? null,
        discountType: p.discountType,
        discountValue: Number(p.discountValue),
        minSubtotalCents: p.minSubtotalCents,
        maxDiscountCents: p.maxDiscountCents ?? null,
        isActive: p.isActive
      }
    });
  } catch (err) {
    return next(err);
  }
});

export default router;
