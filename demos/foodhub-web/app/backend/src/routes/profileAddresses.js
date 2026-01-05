import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, listOk, ok } from '../utils/response.js';
import { rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

const addressSchema = z.object({
  label: z.string().min(1),
  line1: z.string().min(1),
  line2: z.string().optional(),
  city: z.string().min(1),
  state: z.string().min(1),
  postalCode: z.string().min(1),
  lat: z.number().optional(),
  lng: z.number().optional(),
  isDefault: z.boolean().optional()
});

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT id, user_id, label, line1, line2, city, state, postal_code, lat, lng, is_default, created_at
       FROM addresses
       WHERE user_id = $1
       ORDER BY is_default DESC, created_at DESC`,
      [req.user.id]
    );

    const items = rowsToCamel(rows).map((a) => ({
      id: a.id,
      userId: a.userId,
      label: a.label,
      line1: a.line1,
      line2: a.line2 ?? null,
      city: a.city,
      state: a.state,
      postalCode: a.postalCode,
      lat: a.lat !== null && a.lat !== undefined ? Number(a.lat) : null,
      lng: a.lng !== null && a.lng !== undefined ? Number(a.lng) : null,
      isDefault: a.isDefault,
      createdAt: a.createdAt
    }));

    return listOk(res, items, { limit: items.length, offset: 0, total: items.length });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  try {
    const body = addressSchema.parse(req.body);

    if (body.isDefault) {
      await query('UPDATE addresses SET is_default = false WHERE user_id = $1', [req.user.id]);
    }

    const { rows } = await query(
      `INSERT INTO addresses (user_id, label, line1, line2, city, state, postal_code, lat, lng, is_default)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       RETURNING id, user_id, label, line1, line2, city, state, postal_code, lat, lng, is_default, created_at`,
      [
        req.user.id,
        body.label,
        body.line1,
        body.line2 ?? null,
        body.city,
        body.state,
        body.postalCode,
        body.lat ?? null,
        body.lng ?? null,
        body.isDefault ?? false
      ]
    );

    const a = rowsToCamel(rows)[0];
    return ok(res, {
      address: {
        id: a.id,
        userId: a.userId,
        label: a.label,
        line1: a.line1,
        line2: a.line2 ?? null,
        city: a.city,
        state: a.state,
        postalCode: a.postalCode,
        lat: a.lat !== null && a.lat !== undefined ? Number(a.lat) : null,
        lng: a.lng !== null && a.lng !== undefined ? Number(a.lng) : null,
        isDefault: a.isDefault,
        createdAt: a.createdAt
      }
    });
  } catch (err) {
    return next(err);
  }
});

router.delete('/:addressId', requireAuth, async (req, res, next) => {
  try {
    const addressId = z.string().uuid().parse(req.params.addressId);

    const del = await query('DELETE FROM addresses WHERE id = $1 AND user_id = $2', [addressId, req.user.id]);
    if (!del.rowCount) throw new ApiError('NOT_FOUND', 'Address not found', 404);

    return ok(res, { deleted: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
