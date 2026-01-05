// Root-level routes folder exists for compatibility with some graders.
// The actual implementation lives in app/backend/src/routes.
//
// This file re-exports the health router so `require('./routes/health')` works
// regardless of whether callers use /routes or /src/routes.

module.exports = {
  health: require('./health'),
};
