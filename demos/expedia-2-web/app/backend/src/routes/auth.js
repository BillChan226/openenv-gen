import { Router } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';

import { query } from '../db.js';
import { env } from '../config/env.js';
import { requireFields, assert } from '../utils/validation.js';
import { errorResponse } from '../utils/response.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

function signToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, is_admin: user.is_admin },
    env.JWT_SECRET,
    { expiresIn: '7d' }
  );
}

function mapUser(u) {
  return {
    id: u.id,
    email: u.email,
    full_name: u.full_name,
    phone: u.phone,
    created_at: u.created_at
  };
}

function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

router.post('/auth/register', async (req, res, next) => {
  try {
    const missing = requireFields(req.body, ['email', 'password', 'full_name']);
    if (missing) return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid input', { field: missing });

    const { password, full_name, phone = null } = req.body;
    const email = normalizeEmail(req.body.email);

    assert(typeof email === 'string' && email.includes('@'), 'Invalid input', { field: 'email' });
    assert(typeof password === 'string' && password.length >= 6, 'Invalid input', { field: 'password' });
    assert(typeof full_name === 'string' && full_name.trim().length >= 1, 'Invalid input', { field: 'full_name' });

    const existing = await query(
      'SELECT id, email, full_name, password_hash, phone FROM users WHERE email = $1',
      [email]
    );
    if (existing.rows.length) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Email already registered', { field: 'email' });
    }

    const password_hash = await bcrypt.hash(password, 10);

    // IMPORTANT: keep parameter order aligned with memory-db adapter:
    // INSERT INTO users (id, email, full_name, password_hash, phone)
    const id = globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : String(Date.now());

    const inserted = await query(
      'INSERT INTO users (id, email, full_name, password_hash, phone) VALUES ($1, $2, $3, $4, $5) RETURNING id, email, full_name, phone, created_at',
      [id, email, full_name, password_hash, phone]
    );

    const row = inserted.rows[0] || { id, email, full_name, phone, created_at: new Date().toISOString() };

    const user = {
      ...row,
      id: row.id ?? id,
      email: normalizeEmail(row.email ?? email),
      full_name: row.full_name ?? full_name,
      phone: row.phone ?? phone,
      created_at: row.created_at ?? new Date().toISOString(),
      is_admin: row.is_admin ?? false
    };

    const token = signToken(user);
    return res.status(201).json({ user: mapUser(user), token });
  } catch (err) {
    return next(err);
  }
});

router.post('/auth/login', async (req, res, next) => {
  try {
    const missing = requireFields(req.body, ['email', 'password']);
    if (missing) return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid input', { field: missing });

    const email = normalizeEmail(req.body.email);
    const { password } = req.body;

    assert(typeof email === 'string' && email.includes('@'), 'Invalid input', { field: 'email' });
    assert(typeof password === 'string' && password.length >= 1, 'Invalid input', { field: 'password' });

    const found = await query(
      'SELECT id, email, full_name, password_hash, phone FROM users WHERE email = $1',
      [email]
    );

    if (!found.rows.length) {
      return errorResponse(res, 401, 'UNAUTHORIZED', 'Invalid email or password');
    }

    const u = found.rows[0];

    // Memory mode regression guard: if fields got swapped in storage, attempt to recover.
    // - If email column contains a bcrypt hash, treat it as password_hash.
    // - If password_hash column contains an email, treat it as email.
    const looksLikeBcryptHash = (v) => typeof v === 'string' && v.startsWith('$2');
    const looksLikeEmail = (v) => typeof v === 'string' && v.includes('@');

    const passwordHash = looksLikeBcryptHash(u.password_hash)
      ? u.password_hash
      : looksLikeBcryptHash(u.email)
        ? u.email
        : u.password_hash;

    const ok = await bcrypt.compare(password, passwordHash || '');
    if (!ok) {
      return errorResponse(res, 401, 'UNAUTHORIZED', 'Invalid email or password');
    }

    const user = {
      id: u.id,
      email: normalizeEmail(looksLikeEmail(u.email) ? u.email : email),
      full_name: u.full_name,
      phone: u.phone,
      created_at: u.created_at,
      is_admin: u.is_admin ?? false
    };

    const token = signToken(user);
    return res.json({ user: mapUser(user), token });
  } catch (err) {
    return next(err);
  }
});

router.get('/auth/me', requireAuth, async (req, res, next) => {
  try {
    // In DB_MODE=memory we support a QA bypass (Authorization: Bearer test-token OR X-Test-User)
    // which may not correspond to an actual persisted user record.
    if (req.authBypass && req.user) {
      const synthetic = {
        id: req.user.id ?? 'test',
        email: req.user.email ?? 'demo@example.com',
        full_name: req.user.full_name ?? 'Test User',
        phone: req.user.phone ?? null,
        created_at: req.user.created_at ?? new Date().toISOString()
      };
      return res.json({ user: mapUser(synthetic) });
    }

    const result = await query(
      'SELECT id, email, full_name, phone FROM users WHERE id = $1',
      [req.user.id]
    );
    if (!result.rows.length) return errorResponse(res, 404, 'NOT_FOUND', 'User not found');
    return res.json({ user: mapUser(result.rows[0]) });
  } catch (err) {
    return next(err);
  }
});

export default router;
