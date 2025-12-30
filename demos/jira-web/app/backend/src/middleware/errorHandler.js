import { ApiError } from './apiError.js';
import { createLogger } from '../utils/logger.js';
import { config } from '../config/env.js';

const logger = createLogger(config.LOG_LEVEL);

function toErrorResponse(err, statusOverride) {
  const status = statusOverride ?? err?.status ?? 500;
  const code = err?.code ?? 'server_error';

  const message =
    status === 500 && config.NODE_ENV === 'production' ? 'An error occurred' : err?.message || 'An error occurred';

  return {
    status,
    body: {
      error: {
        code,
        message,
        details: err?.details ?? null,
      },
    },
  };
}

export function notFoundHandler(req, res) {
  return res.status(404).json({
    error: {
      code: 'not_found',
      message: 'Route not found',
      details: { path: req.originalUrl },
    },
  });
}

export function errorHandler(err, req, res, _next) {
  const status = err?.status || 500;

  logger.error('Request error', {
    status,
    code: err?.code,
    message: err?.message,
    stack: err?.stack,
    path: req.originalUrl,
    method: req.method,
    userId: req.user?.id,
  });

  // Handle PG errors in a consistent way
  if (err?.code?.startsWith?.('23')) {
    const { status: s, body } = toErrorResponse(
      new ApiError(400, 'validation_error', 'Database constraint violation', {
        pg: err.code,
        detail: err.detail,
      })
    );
    return res.status(s).json(body);
  }

  const { status: s, body } = toErrorResponse(err instanceof ApiError ? err : err, status);
  return res.status(s).json(body);
}
