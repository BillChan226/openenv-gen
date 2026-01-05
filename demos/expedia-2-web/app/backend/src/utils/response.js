export function okList(res, { items, total, limit, offset }) {
  const payload = { items };
  if (typeof total === 'number') payload.total = total;
  if (typeof limit === 'number') payload.limit = limit;
  if (typeof offset === 'number') payload.offset = offset;
  return res.json(payload);
}

export function okItem(res, itemKey, item) {
  return res.json({ [itemKey]: item });
}

export function errorResponse(res, status, code, message, details = null) {
  return res.status(status).json({ error: { code, message, details } });
}
