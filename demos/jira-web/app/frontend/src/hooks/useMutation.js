import { useCallback, useState } from 'react';

export function useMutation(mutationFn) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const mutate = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        return await mutationFn(...args);
      } catch (e) {
        setError(e?.message || 'Request failed');
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [mutationFn]
  );

  return { mutate, loading, error, setError };
}
