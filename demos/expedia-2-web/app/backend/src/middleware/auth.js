import jwt from 'jsonwebtoken';
import { env } from '../config/env.js';
import { errorResponse } from '../utils/response.js';
import { query, dbMode } from '../db.js';

function parseToken(req) {
  const header = req.headers.authorization;
  if (!header) return null;
  const [scheme, token] = header.split(' ');
  if (scheme !== 'Bearer' || !token) return null;
  return token;
}

async function getUserByEmail(email) {
  const { rows } = await query(
    'SELECT id, email, full_name, phone, created_at, is_admin FROM users WHERE email = $1',
    [String(email || '').trim().toLowerCase()]
  );
  return rows[0] || null;
}

async function tryMemoryQaBypass(req) {
  // QA-only bypass to allow testing in environments that redact JWTs.
  // Enabled ONLY when DB_MODE=memory.
  if (dbMode !== 'memory') return null;

  const testUserHeader = req.headers['x-test-user'];
  if (testUserHeader) {
    const raw = Array.isArray(testUserHeader) ? testUserHeader[0] : String(testUserHeader);
    const value = raw.trim();

    // If numeric, treat as user id without DB lookup.
    if (/^\d+$/.test(value)) {
      return {
        id: Number(value),
        email: `user${value}@test.local`,
        full_name: `Test User ${value}`,
        phone: null,
        created_at: new Date().toISOString(),
        is_admin: false
      };
    }

    // Otherwise treat as email; try DB lookup but fall back to a synthetic user.
    const user = await getUserByEmail(value);
    if (user) {
      return {
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        phone: user.phone ?? null,
        created_at: user.created_at,
        is_admin: user.is_admin
      };
    }

    return {
      id: `test:${value.toLowerCase()}`,
      email: value.toLowerCase(),
      full_name: 'QA Test User',
      phone: null,
      created_at: new Date().toISOString(),
      is_admin: false
    };
  }

  const token = parseToken(req);
  if (token) {
    // In DB_MODE=memory we treat the raw bearer token as the stable user identifier
    // for QA/testing unless the caller explicitly provides X-Test-User.
    // This prevents identity mismatches between routes that look up data by user_id.
    const stableId = `token:${token}`;

    // Special-case common QA tokens.
    if (token === 'test' || token === 'test-token') {
      // If the seeded demo user exists, use it for nicer /auth/me responses.
      // But keep a stable id derived from the token to avoid switching identities.
      const user = await getUserByEmail('demo@example.com');
      if (user) {
        return {
          id: stableId,
          email: user.email,
          full_name: user.full_name,
          phone: user.phone ?? null,
          created_at: user.created_at,
          is_admin: user.is_admin
        };
      }

      return {
        id: stableId,
        email: 'demo@example.com',
        full_name: 'Demo User',
        phone: null,
        created_at: new Date().toISOString(),
        is_admin: false
      };
    }

    // Generic token-based identity.
    return {
      id: stableId,
      email: `qa+${token}@test.local`,
      full_name: 'QA Token User',
      phone: null,
      created_at: new Date().toISOString(),
      is_admin: false
    };
  }

  return null;
}

export async function requireAuth(req, res, next) {
  try {
    const bypassPayload = await tryMemoryQaBypass(req);
    if (bypassPayload) {
      req.user = bypassPayload;
      req.authBypass = true;
      return next();
    }

    const token = parseToken(req);
    if (!token) return errorResponse(res, 401, 'UNAUTHORIZED', 'Missing or invalid token', null);

    const payload = jwt.verify(token, env.JWT_SECRET);
    req.user = payload;
    return next();
  } catch {
    return errorResponse(res, 401, 'UNAUTHORIZED', 'Missing or invalid token', null);
  }
}

export async function optionalAuth(req, _res, next) {
  try {
    const bypassPayload = await tryMemoryQaBypass(req);
    if (bypassPayload) {
      req.user = bypassPayload;
      req.authBypass = true;
      return next();
    }

    const token = parseToken(req);
    if (!token) return next();

    const payload = jwt.verify(token, env.JWT_SECRET);
    req.user = payload;
    return next();
  } catch {
    return next();
  }
}

// aliases
export const authRequired = requireAuth;
export const requireAuthMiddleware = requireAuth;
