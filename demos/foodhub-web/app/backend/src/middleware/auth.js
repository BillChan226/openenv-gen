import jwt from 'jsonwebtoken';
import { ApiError } from '../utils/response.js';
import { query } from '../db.js';

const isTestMode = process.env.DB_MODE === 'memory' || process.env.NODE_ENV === 'test';

export const requireAuth = async (req, _res, next) => {
  if (isTestMode) {
    const authHeader = req.headers.authorization;
    const testUser = req.headers['x-test-user'];
    if (authHeader === 'Bearer test' || authHeader === 'Bearer test-token') {
      req.user = { id: 'test-user-1', email: 'test@test.com', fullName: 'Test User' };
      return next();
    }
    if (testUser) {
      req.user = { id: String(testUser), email: `${testUser}@test.com`, fullName: 'Test User' };
      return next();
    }
  }

  const header = req.headers.authorization || '';
  if (!header.startsWith('Bearer ')) return next(new ApiError('UNAUTHORIZED', 'Missing token', 401));
  const token = header.slice('Bearer '.length);

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET || 'dev_secret');

    // Validate that the user still exists in DB. This prevents downstream 500s
    // (e.g., cart creation FK violations) when tokens reference deleted/unknown users.
    const { rows } = await query('SELECT id, email, full_name FROM users WHERE id = $1', [payload.sub]);
    const user = rows[0];
    if (!user) return next(new ApiError('UNAUTHORIZED', 'User not found', 401));

    req.user = { id: user.id, email: user.email, fullName: user.full_name };
    return next();
  } catch {
    return next(new ApiError('UNAUTHORIZED', 'Invalid token', 401));
  }
};

export const optionalAuth = (req, res, next) => {
  const header = req.headers.authorization || '';
  if (!header) return next();
  return requireAuth(req, res, next);
};

export const authRequired = requireAuth;
