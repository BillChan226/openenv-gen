import { env } from '../config/env.js';

export function parseLimitOffset(req, defaultLimit = env.NODE_ENV === 'test' ? 20 : 20) {
  const limitRaw = req.query.limit;
  const offsetRaw = req.query.offset;

  let limit = Number.isFinite(Number(limitRaw)) ? Number(limitRaw) : defaultLimit;
  let offset = Number.isFinite(Number(offsetRaw)) ? Number(offsetRaw) : 0;

  if (limit < 1) limit = 1;
  if (limit > 100) limit = 100;
  if (offset < 0) offset = 0;

  return { limit, offset };
}
