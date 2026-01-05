// Compatibility shim for legacy imports.
// Route files in src/ expect: const db = require('../db')
// which resolves to app/backend/db.js when required from app/backend/src/*.
// The actual implementation lives in src/db.js.

module.exports = require('./src/db');
