const express = require('express');
const { z } = require('zod');

const db = require('../db');
const { requireAuth } = require('../middleware/auth');
const { itemResponse, errorResponse } = require('../utils/responses');

const router = express.Router();

function toUser(row) {
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    phone: row.phone,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const result = await db.query(
      'SELECT id,email,name,phone,created_at,updated_at FROM users WHERE id=$1',
      [req.user.id]
    );
    if (result.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'User not found');
    return itemResponse(res, { user: toUser(result.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

router.patch('/me', requireAuth, async (req, res, next) => {
  try {
    const schema = z
      .object({
        name: z.string().min(1).optional(),
        email: z.string().email().optional(),
        phone: z.string().nullable().optional(),
      })
      .refine((v) => Object.keys(v).length > 0, { message: 'At least one field is required' });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid request body', parsed.error.flatten());
    }

    const { name, email, phone } = parsed.data;

    if (email) {
      const existing = await db.query('SELECT id FROM users WHERE email=$1 AND id<>$2', [email, req.user.id]);
      if (existing.rowCount > 0) {
        return errorResponse(res, 409, 'EMAIL_IN_USE', 'Email is already in use');
      }
    }

    const updated = await db.query(
      `UPDATE users
       SET name = COALESCE($1, name),
           email = COALESCE($2, email),
           phone = $3,
           updated_at = now()
       WHERE id=$4
       RETURNING id,email,name,phone,created_at,updated_at`,
      [name ?? null, email ?? null, phone ?? null, req.user.id]
    );

    if (updated.rowCount === 0) return errorResponse(res, 404, 'NOT_FOUND', 'User not found');
    return itemResponse(res, { user: toUser(updated.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
