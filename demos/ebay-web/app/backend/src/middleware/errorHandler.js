import { logger } from '../utils/logger.js';

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  static badRequest(message, details) {
    return new ApiError(400, 'validation_error', message, details);
  }

  static unauthorized(message = 'Unauthorized') {
    return new ApiError(401, 'unauthorized', message);
  }

  static forbidden(message = 'Forbidden') {
    return new ApiError(403, 'forbidden', message);
  }

  static notFound(message = 'Not found') {
    return new ApiError(404, 'not_found', message);
  }
}

export function notFoundHandler(req, res, next) {
  next(ApiError.notFound(`Route not found: ${req.method} ${req.originalUrl}`));
}

export function errorHandler(err, req, res, next) {
  const status = err.status || 500;
  const code = err.code || 'server_error';

  logger.error(err.message || 'Unhandled error', {
    code,
    status,
    path: req.originalUrl,
    method: req.method,
    userId: req.user?.id,
    stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
  });

  const message =
    process.env.NODE_ENV === 'production' && status === 500 ? 'An error occurred' : err.message;

  res.status(status).json({
    error: {
      code,
      message,
      details: err.details || null
    }
  });
}
