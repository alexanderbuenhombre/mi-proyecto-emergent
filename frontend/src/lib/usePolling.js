import { useEffect, useRef, useState } from "react";

/**
 * Polling hook with strict race-condition safety:
 *  - each effect run has its own generation id
 *  - stale in-flight responses are ignored
 *  - only one timer chain per effect run
 */
export function usePolling(fn, intervalMs, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const genRef = useRef(0);

  useEffect(() => {
    genRef.current += 1;
    const myGen = genRef.current;
    let timer = null;
    let cancelled = false;

    const run = async () => {
      try {
        const res = await fn();
        if (cancelled || myGen !== genRef.current) return;
        setData(res);
        setError(null);
        setLoading(false);
      } catch (e) {
        if (cancelled || myGen !== genRef.current) return;
        setError(e);
        setLoading(false);
      }
      if (!cancelled && myGen === genRef.current) {
        timer = setTimeout(run, intervalMs);
      }
    };
    run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading };
}
