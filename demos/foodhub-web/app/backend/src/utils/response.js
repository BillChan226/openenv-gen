export const ok = (res, data = {}) => res.json({ success: true, data });

export const created = (res, data = {}) => res.status(201).json({ success: true, data });

export const listOk = (res, items, pagination) =>
  res.json({ success: true, data: { items, pagination } });

export class ApiError extends Error {
  constructor(code, message, http = 400, details = undefined) {
    super(message);
    this.code = code;
    this.http = http;
    this.details = details;
  }
}

export const errorResponse = (res, err) => {
  const http = err.http || 500;
  const code = err.code || 'INTERNAL_ERROR';
  const message = err.message || 'Internal error';
  const details = err.details;
  return res.status(http).json({ success: false, error: { code, message, details } });
};
