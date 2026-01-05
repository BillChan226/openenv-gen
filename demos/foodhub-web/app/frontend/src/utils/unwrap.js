export function unwrapResponse(response) {
  const data = response?.data;
  if (!data) return data;

  // Standard wrapper: { success: true, data: ... }
  if (typeof data === 'object' && 'success' in data) {
    if (data.success === false) return data;
    return data.data;
  }

  // Common wrapper: { data: ... }
  if (typeof data === 'object' && 'data' in data && data.data !== undefined) {
    return data.data;
  }

  return data;
}

export function unwrapItems(response) {
  const data = unwrapResponse(response);
  if (!data) return { items: [], pagination: null };

  if (Array.isArray(data)) return { items: data, pagination: null };
  if (data.items) return { items: data.items, pagination: data.pagination || null };

  // fallback: single-key wrapper inside data
  const keys = Object.keys(data || {});
  if (keys.length === 1 && data[keys[0]]?.items) {
    return { items: data[keys[0]].items, pagination: data[keys[0]].pagination || null };
  }

  return { items: [], pagination: null };
}
