const jwt = require('jsonwebtoken');

const { errorResponse } = require('../utils/responses');

function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) return errorResponse(res, 401, 'UNAUTHORIZED', 'Missing Authorization Bearer token');

  const token = match[1];
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET || 'dev_secret', {
      issuer: process.env.JWT_ISSUER || 'voyager',
      audience: process.env.JWT_AUDIENCE || 'voyager-web',
    });
    req.user = { id: payload.sub, email: payload.email };
    return next();
  } catch (e) {
    return errorResponse(res, 401, 'UNAUTHORIZED', 'Invalid or expired token');
  }
}

module.exports = {
  requireAuth,
};
