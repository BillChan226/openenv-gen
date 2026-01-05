import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';

export function useQueryParams() {
  const { search } = useLocation();
  return useMemo(() => {
    const sp = new URLSearchParams(search);
    const obj = {};
    for (const [k, v] of sp.entries()) obj[k] = v;
    return obj;
  }, [search]);
}

export default useQueryParams;
