import jwt from 'jsonwebtoken';
import { ApiError } from './errorHandler.js';
import { config } from '../config/env.js';
import { isJwtSessionActive } from '../services/sessionStore.js';

function getBearerToken(req) {
  // Express/Node lower-case header keys.
  // Support common variations and guard against proxies that might strip/rename.
  const header =
    req.headers?.authorization ||
    req.headers?.Authorization ||
    req.get?.('authorization') ||
    req.get?.('Authorization');

  if (!header) return null;
  if (Array.isArray(header)) {
    // If multiple Authorization headers are present, take the first.
    return header.length ? header[0].replace(/^Bearer\s+/i, '').trim() : null;
  }

  const value = String(header);
  const m = value.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;
  return m[1].trim();
}

function getTokenFallback(req) {
  // Test/QA-friendly fallback for environments where clients cannot set headers.
  // Disabled in production.
  if (config.NODE_ENV === 'production') return null;

  // Prefer explicit query param.
  const accessToken = req.query?.access_token;
  if (accessToken) return String(accessToken).trim();

  // Allow passing token in body for QA tooling (e.g., POST /api/auth/me).
  const bodyToken = req.body?.token;
  if (bodyToken) return String(bodyToken).trim();

  // Optional cookie support (only if cookie-parser is installed/used).
  const cookieToken = req.cookies?.access_token;
  if (cookieToken) return String(cookieToken).trim();

  return null;
}

function getAuthToken(req) {
  return getBearerToken(req) || getTokenFallback(req);
}

export function authRequired(req, res, next) {
  const token = getAuthToken(req);
  if (!token) return next(ApiError.unauthorized('Missing token'));

  try {
    const payload = jwt.verify(token, config.JWT_SECRET);

    // Prefer stateless JWT auth. If a server-side session exists for this jti,
    // enforce it (so logout/revocation works). If no session is found, still
    // allow the request to proceed (QA/demo friendly and avoids cross-process
    // in-memory session issues).
    if (payload?.jti) {
      const active = isJwtSessionActive(payload.jti);
      // If the session store knows about this jti and it's inactive, reject.
      // If it doesn't know about it (e.g., server restarted), accept based on JWT.
      if (active === false) {
        return next(ApiError.unauthorized('Session expired'));
      }
    }

    req.user = payload;
    return next();
  } catch {
    return next(ApiError.unauthorized('Invalid token'));
  }
}

export function authOptional(req, res, next) {
  const token = getAuthToken(req);
  if (token) {
    try {
      const payload = jwt.verify(token, config.JWT_SECRET);
      if (payload?.jti) {
        const active = isJwtSessionActive(payload.jti);
        if (active === false) {
          // known + revoked/expired
          return next(ApiError.unauthorized('Session expired'));
        }
      }
      req.user = payload;
    } catch {
      // ignore
    }
  }
  next();
}
