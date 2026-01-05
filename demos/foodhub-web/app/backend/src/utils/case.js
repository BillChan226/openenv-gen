const toCamel = (s) => s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());

export const rowToCamel = (row) => {
  if (!row || typeof row !== 'object') return row;
  const out = {};
  for (const [k, v] of Object.entries(row)) out[toCamel(k)] = v;
  return out;
};

export const rowsToCamel = (rows = []) => rows.map(rowToCamel);
