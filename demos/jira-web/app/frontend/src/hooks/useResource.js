import { useCallback, useEffect, useRef, useState } from 'react';

export function useResource(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Avoid infinite refetch loops when callers pass an inline fetchFn.
  // Keep the latest fetchFn in a ref and make refetch stable.
  const fetchRef = useRef(fetchFn);
  const inFlightRef = useRef(false);

  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  const refetch = useCallback(async () => {
    if (inFlightRef.current) return null;

    inFlightRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRef.current();
      setData(res);
      return res;
    } catch (e) {
      setError(e?.message || 'Failed to load data');
      return null;
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }, []);

  // Only refetch when deps change (not when fetchFn identity changes).
  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, refetch, setData };
}
