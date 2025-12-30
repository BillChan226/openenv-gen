import express from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';

import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';
import { authRequired } from '../middleware/auth.js';
import { config } from '../config/env.js';

const router = express.Router();

function signToken(user) {
  // Include a unique token id (jti) so we can revoke tokens on logout.
  // We use a UUID string to match the DB schema.
  const jti = crypto.randomUUID();
  return jwt.sign(
    {
      jti,
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
    },
    config.JWT_SECRET,
    { expiresIn: config.JWT_EXPIRES_IN }
  );
}

function getTokenFromRequest(req) {
  const header = req.headers.authorization || '';
  const bearer = header.startsWith('Bearer ') ? header.slice('Bearer '.length) : null;
  if (bearer) return bearer;

  const cookieToken = req.cookies?.access_token;
  if (cookieToken) return cookieToken;

  // Test-mode escape hatch (mirrors middleware behavior)
  if (config.AUTH_TEST_MODE === true && config.NODE_ENV !== 'production') {
    const testHeaderToken = req.headers['x-test-auth'];
    if (typeof testHeaderToken === 'string' && testHeaderToken.trim()) return testHeaderToken.trim();

    const bodyToken = req.body?.auth_token;
    if (typeof bodyToken === 'string' && bodyToken.trim()) return bodyToken.trim();

    const queryToken = req.query?.auth_token;
    if (typeof queryToken === 'string' && queryToken.trim()) return queryToken.trim();
  }

  if (config.NODE_ENV === 'test') {
    const bodyToken = req.body?.auth_token;
    if (typeof bodyToken === 'string' && bodyToken.trim()) return bodyToken.trim();

    const queryToken = req.query?.auth_token;
    if (typeof queryToken === 'string' && queryToken.trim()) return queryToken.trim();
  }

  return null;
}

// POST /api/auth/login
router.post('/login', async (req, res, next) => {
  try {
    const { email, password } = req.body ?? {};

    if (!email || !password) {
      return next(ApiError.badRequest('email and password are required', { fields: ['email', 'password'] }));
    }

    const { rows } = await pool.query(
      'SELECT id, email, password_hash, name, role, avatar_url FROM app_user WHERE email = $1 LIMIT 1',
      [email]
    );

    const userRow = rows[0];
    if (!userRow) {
      return next(ApiError.unauthorized('Invalid email or password'));
    }

    const ok = await bcrypt.compare(password, userRow.password_hash);
    if (!ok) {
      return next(ApiError.unauthorized('Invalid email or password'));
    }

    const user = {
      id: userRow.id,
      email: userRow.email,
      name: userRow.name,
      role: userRow.role,
      avatarUrl: userRow.avatar_url,
    };

    const token = signToken(user);

    // Cookie-based session persistence
    const isProd = config.NODE_ENV === 'production';
    res.cookie('access_token', token, {
      httpOnly: true,
      secure: isProd,
      sameSite: isProd ? 'none' : 'lax',
      maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return res.status(200).json({ token, user });
  } catch (err) {
    // Provide a clear, non-crashing response when DB is unavailable or schema isn't initialized.
    // Common cases in local verification:
    // - Postgres not running (ECONNREFUSED)
    // - wrong credentials
    // - init scripts/migrations not applied (missing table)
    if (err?.code === 'ECONNREFUSED' || err?.code === 'ENOTFOUND') {
      return next(ApiError.serviceUnavailable('Database unavailable', { reason: err.code }));
    }
    if (err?.code === '28P01') {
      return next(ApiError.serviceUnavailable('Database authentication failed', { pg: err.code }));
    }
    if (err?.code === '3D000') {
      return next(ApiError.serviceUnavailable('Database does not exist', { pg: err.code }));
    }
    if (err?.code === '42P01') {
      return next(
        ApiError.serviceUnavailable('Database schema not initialized (missing tables). Run init scripts/migrations.', {
          pg: err.code,
        })
      );
    }

    return next(err);
  }
});

// POST /api/auth/test-login
// Verification/test endpoint to obtain a JWT without relying on cookie persistence.
// Enabled only when AUTH_TEST_MODE=true (or NODE_ENV==='test') and never in production.
router.post('/test-login', async (req, res, next) => {
  try {
    const enabled = (config.AUTH_TEST_MODE === true || config.NODE_ENV === 'test') && config.NODE_ENV !== 'production';
    if (!enabled) {
      return next(ApiError.notFound('Not found'));
    }

    const { email } = req.body ?? {};
    if (!email) {
      return next(ApiError.badRequest('email is required', { fields: ['email'] }));
    }

    const { rows } = await pool.query(
      'SELECT id, email, name, role, avatar_url FROM app_user WHERE email = $1 LIMIT 1',
      [email]
    );

    const userRow = rows[0];
    if (!userRow) {
      return next(ApiError.unauthorized('User not found'));
    }

    const user = {
      id: userRow.id,
      email: userRow.email,
      name: userRow.name,
      role: userRow.role,
      avatarUrl: userRow.avatar_url,
    };

    const test_token = signToken(user);

    // Also set the cookie so browser-based flows still work in test mode.
    res.cookie('access_token', test_token, {
      httpOnly: true,
      secure: false,
      sameSite: 'lax',
      maxAge: 1000 * 60 * 60 * 24 * 7,
      path: '/',
    });

    return res.status(200).json({ test_token, user });
  } catch (err) {
    return next(err);
  }
});

// POST /api/auth/logout
// Logout must revoke the presented JWT so it cannot be used again.
router.post('/logout', authRequired, async (req, res, next) => {
  try {
    const token = getTokenFromRequest(req);
    if (!token) return next(ApiError.unauthorized('Missing token'));

    const decoded = jwt.decode(token);
    const jti = decoded?.jti;
    const exp = decoded?.exp;

    if (jti && exp) {
      const expiresAt = new Date(exp * 1000);
      // Insert revocation. If already revoked, no-op.
      await pool.query(
        'INSERT INTO revoked_jwt (jti, expires_at) VALUES ($1, $2) ON CONFLICT (jti) DO NOTHING',
        [jti, expiresAt]
      );
    }

    const isProd = config.NODE_ENV === 'production';
    res.clearCookie('access_token', {
      httpOnly: true,
      secure: isProd,
      sameSite: isProd ? 'none' : 'lax',
      path: '/',
    });

    return res.status(204).send();
  } catch (err) {
    return next(err);
  }
});

// GET /api/auth/me
router.get('/me', authRequired, async (req, res, next) => {
  try {
    const userId = req.user?.id;
    if (!userId) return next(ApiError.unauthorized('Invalid token'));

    const { rows } = await pool.query(
      'SELECT id, email, name, role, avatar_url FROM app_user WHERE id = $1 LIMIT 1',
      [userId]
    );

    const userRow = rows[0];
    if (!userRow) return next(ApiError.unauthorized('User not found'));

    return res.status(200).json({
      user: {
        id: userRow.id,
        email: userRow.email,
        name: userRow.name,
        role: userRow.role,
        avatarUrl: userRow.avatar_url,
      },
    });
  } catch (err) {
    return next(err);
  }
});

export default router;
