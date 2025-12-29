import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';

import { config } from './config/env.js';
import { corsMiddleware } from './config/cors.js';
import { requestLogger } from './middleware/requestLogger.js';
import { apiLimiter } from './middleware/rateLimiters.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

import healthRoutes from './routes/health.js';
import authRoutes from './routes/auth.js';
import catalogRoutes from './routes/catalog.js';
import searchRoutes from './routes/search.js';
import cartRoutes from './routes/cart.js';
import wishlistRoutes from './routes/wishlist.js';
import accountRoutes from './routes/account.js';

export function createApp() {
  const app = express();

  app.disable('x-powered-by');
  app.use(helmet());
  app.use(corsMiddleware);
  app.use(express.json({ limit: '1mb' }));

  // Cookie support (for QA tools / browser sessions)
  // We avoid adding cookie-parser dependency; this lightweight parser is enough
  // for reading our own access_token cookie.
  app.use((req, _res, next) => {
    const header = req.headers?.cookie;
    if (!header) return next();
    const cookies = {};
    const parts = String(header).split(';');
    for (const part of parts) {
      const [k, ...rest] = part.split('=');
      if (!k) continue;
      const key = k.trim();
      const value = rest.join('=').trim();
      if (!key) continue;
      cookies[key] = decodeURIComponent(value);
    }
    req.cookies = cookies;
    return next();
  });

  // Minimal res.cookie/res.clearCookie polyfill so routes can set HttpOnly cookies
  // without needing the cookie-parser dependency.
  app.use((req, res, next) => {
    res.cookie = (name, value, options = {}) => {
      const opts = {
        path: '/',
        httpOnly: false,
        secure: false,
        sameSite: 'lax',
        ...options
      };

      let cookie = `${name}=${encodeURIComponent(String(value))}`;
      if (opts.maxAge != null) cookie += `; Max-Age=${Math.floor(Number(opts.maxAge) / 1000)}`;
      if (opts.expires) cookie += `; Expires=${new Date(opts.expires).toUTCString()}`;
      if (opts.domain) cookie += `; Domain=${opts.domain}`;
      if (opts.path) cookie += `; Path=${opts.path}`;
      if (opts.httpOnly) cookie += '; HttpOnly';
      if (opts.secure) cookie += '; Secure';
      if (opts.sameSite) cookie += `; SameSite=${opts.sameSite}`;

      const prev = res.getHeader('Set-Cookie');
      if (!prev) res.setHeader('Set-Cookie', cookie);
      else if (Array.isArray(prev)) res.setHeader('Set-Cookie', [...prev, cookie]);
      else res.setHeader('Set-Cookie', [prev, cookie]);

      return res;
    };

    res.clearCookie = (name, options = {}) => {
      return res.cookie(name, '', { ...options, expires: new Date(0), maxAge: 0 });
    };

    // Expose for downstream handlers if needed
    req.res = res;
    next();
  });


  if (config.NODE_ENV !== 'production') {
    app.use(morgan('dev'));
  }
  app.use(requestLogger);

  app.use(apiLimiter);

  // Root health
  app.use(healthRoutes);

  // Auth
  // Primary mount under /api/auth to match the rest of the API surface.
  app.use('/api/auth', authRoutes);
  // Backward-compatible alias.
  app.use('/auth', authRoutes);

  // API
  // Contract mounts
  app.use('/api/catalog', catalogRoutes);
  app.use('/api/search', searchRoutes);

  // Backward-compatible aliases (common client conventions)
  // Many clients call /api/products and /api/categories directly.
  // We mount the catalog router at these paths so endpoints like:
  //   GET /api/products?limit=5
  //   GET /api/products/:id
  //   GET /api/categories
  // continue to work.
  app.use('/api', catalogRoutes);

  // Other API surfaces
  app.use('/api/cart', cartRoutes);
  app.use('/api/wishlist', wishlistRoutes);
  app.use('/api/account', accountRoutes);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
