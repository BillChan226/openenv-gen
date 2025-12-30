import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import cookieParser from 'cookie-parser';

import { config } from './config/env.js';
import { apiLimiter, skipAuthBootstrapLimiter } from './middleware/rateLimiters.js';
import { requestLogger } from './middleware/requestLogger.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

import authRoutes from './routes/auth.js';
import userRoutes from './routes/users.js';
import projectRoutes from './routes/projects.js';
import issueRoutes from './routes/issues.js';
import commentRoutes from './routes/comments.js';
import searchRoutes from './routes/search.js';
import settingsRoutes from './routes/settings.js';
import healthRoutes from './routes/health.js';

const app = express();

app.use(
  cors({
    origin: config.FRONTEND_URL,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);
app.use(helmet());
app.use(cookieParser());
app.use(express.json({ limit: '1mb' }));
app.use(morgan(config.NODE_ENV === 'production' ? 'combined' : 'dev'));
app.use(requestLogger);

// Trust proxy so rate limiting uses the correct client IP when behind docker/reverse proxies.
// In local dev this also prevents all requests being treated as coming from a single IP.
app.set('trust proxy', 1);

// Apply global API limiter, but do not let it block auth bootstrap endpoints in dev.
app.use('/api', skipAuthBootstrapLimiter, apiLimiter);

// Root health (no /api prefix)
app.use(healthRoutes);

// API routes
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/projects', projectRoutes);
app.use('/api/issues', issueRoutes);
app.use('/api/comments', commentRoutes);
app.use('/api/search', searchRoutes);
app.use('/api/settings', settingsRoutes);

app.use(notFoundHandler);
app.use(errorHandler);

export default app;
