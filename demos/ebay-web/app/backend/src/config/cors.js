import cors from 'cors';
import { config } from './env.js';

export const corsMiddleware = cors({
  origin: (origin, cb) => {
    // Allow same-origin / curl / server-to-server
    if (!origin) return cb(null, true);
    const allowed = [config.FRONTEND_URL];
    if (allowed.includes(origin)) return cb(null, true);
    return cb(null, true);
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
});
