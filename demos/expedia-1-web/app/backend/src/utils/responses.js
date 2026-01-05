function listResponse(res, items, total, page, limit) {
  return res.json({ items, total, page, limit });
}

function itemResponse(res, item) {
  return res.json({ item });
}

function errorResponse(res, status, code, message, details) {
  // Provide a consistent error shape for the frontend.
  // Include `status` to make it easier for clients to display friendly messages
  // for network/dependency failures (e.g., 503 Service Unavailable).
  return res.status(status).json({
    error: {
      status,
      code,
      message,
      ...(details ? { details } : {}),
    },
  });
}

module.exports = {
  listResponse,
  itemResponse,
  errorResponse,
};
