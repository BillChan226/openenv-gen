// Utility helpers to support multiple query param naming conventions.
// The UI/spec may use camelCase while the DB/API originally used snake_case.

function firstDefined(obj, keys) {
  for (const k of keys) {
    if (obj[k] !== undefined) return obj[k];
  }
  return undefined;
}

/**
 * Returns a shallow-cloned query object with alias keys mapped to canonical keys.
 * Does NOT delete original keys; zod will ignore unknown keys by default.
 */
function applyQueryAliases(query, aliasMap) {
  const q = { ...query };
  for (const [canonical, aliases] of Object.entries(aliasMap)) {
    if (q[canonical] === undefined) {
      const v = firstDefined(q, aliases);
      if (v !== undefined) q[canonical] = v;
    }
  }
  return q;
}

module.exports = { applyQueryAliases };
