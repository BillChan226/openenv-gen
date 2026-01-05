import { errorResponse } from '../utils/response.js';

export function notFound(_req, res) {
  return errorResponse(res, 404, 'NOT_FOUND', 'Not found', null);
}

export function errorHandler(err, _req, res, _next) {
  const status = err.status || 500;
  const code = err.code || (status === 500 ? 'INTERNAL_ERROR' : 'ERROR');
  const message = err.message || 'Server error';
  const details = err.details ?? null;

  if (status >= 500) {
    // eslint-disable-next-line no-undef
    console.error(err);
  }

  return errorResponse(res, status, code, message, details);
}
