import { ApiError, errorResponse } from '../utils/response.js';

export const notFoundHandler = (req, _res, next) => {
  next(new ApiError('NOT_FOUND', `Route not found: ${req.method} ${req.originalUrl}`, 404));
};

export const errorHandler = (err, req, res, _next) => {
  // Always log enough context to debug from Docker logs.
  // (morgan logs requests; this logs stack traces and payload details.)
  const requestMeta = {
    method: req?.method,
    path: req?.originalUrl,
    userId: req?.user?.id,
    ip: req?.ip
  };

  if (err instanceof ApiError) {
    console.error('[API_ERROR]', requestMeta, {
      code: err.code,
      message: err.message,
      status: err.status,
      details: err.details
    });
    return errorResponse(res, err);
  }

  // zod
  if (err?.name === 'ZodError') {
    console.error('[VALIDATION_ERROR]', requestMeta, { issues: err.issues });
    return errorResponse(
      res,
      new ApiError('VALIDATION_ERROR', 'Validation error', 400, { issues: err.issues })
    );
  }

  console.error('[UNHANDLED_ERROR]', requestMeta);
  console.error(err?.stack || err);
  return errorResponse(res, new ApiError('INTERNAL_ERROR', 'Internal error', 500));
};
