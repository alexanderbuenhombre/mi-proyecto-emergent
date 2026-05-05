import { useEffect, useRef, useState } from "react";

export function usePolling(fn, intervalMs, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let timer;
    const run = async () => {
      try {
        const res = await fn();
        if (mountedRef.current) {
          setData(res);
          setError(null);
          setLoading(false);
        }
      } catch (e) {
        if (mountedRef.current) {
          setError(e);
          setLoading(false);
        }
      }
      if (mountedRef.current) timer = setTimeout(run, intervalMs);
    };
    run();
    return () => {
      mountedRef.current = false;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading };
}
