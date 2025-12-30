import { createLogger } from '../utils/logger.js';
import { config } from '../config/env.js';

const logger = createLogger(config.LOG_LEVEL);

export function requestLogger(req, res, next) {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info(`${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`, {
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration,
      userId: req.user?.id,
    });
  });
  next();
}
