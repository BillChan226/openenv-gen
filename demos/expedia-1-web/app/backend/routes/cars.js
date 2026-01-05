// Compatibility re-export.
// Some deployments expect routes to live in app/backend/routes.
// The actual implementation lives in app/backend/src/routes.

module.exports = require('../src/routes/cars');
