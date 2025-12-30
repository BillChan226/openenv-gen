import rateLimit from 'express-rate-limit';

export const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'rate_limit', message: 'Too many requests', details: null },
});

const isDev = process.env.NODE_ENV !== 'production';

export const authLimiter = rateLimit({
  // In dev we keep this lenient to avoid blocking local login due to refreshes/hot reload.
  windowMs: 15 * 60 * 1000,
  max: isDev ? 200 : 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'rate_limit', message: 'Too many auth attempts', details: null },
});

// Global API limiter should not block auth bootstrap endpoints in dev.
// This is applied at the router level (see app.js) and can be used as a no-op in dev.
export const skipAuthBootstrapLimiter = (req, _res, next) => {
  if (!isDev) return next();
  const p = req.path || '';
  if (p === '/auth/me' || p === '/auth/login' || p === '/auth/logout') return next();
  return next();
};
