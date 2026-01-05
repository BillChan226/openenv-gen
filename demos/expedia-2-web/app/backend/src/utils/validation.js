import { errorResponse } from './response.js';

export function requireFields(body, fields) {
  for (const f of fields) {
    if (body?.[f] === undefined || body?.[f] === null || body?.[f] === '') {
      return f;
    }
  }
  return null;
}

export function assert(condition, message, details) {
  if (!condition) {
    const err = new Error(message);
    err.status = 400;
    err.code = 'VALIDATION_ERROR';
    err.details = details ?? null;
    throw err;
  }
}

export function validateUUID(id) {
  return typeof id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id);
}

export function validationError(res, message, details = null) {
  return errorResponse(res, 400, 'VALIDATION_ERROR', message, details);
}
