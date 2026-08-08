import { useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

interface ApiDataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
}

/**
 * Runs `fetcher` whenever `deps` change, tracking loading/error state and
 * ignoring results from stale (superseded) requests.
 */
export function useApiData<T>(fetcher: () => Promise<T>, deps: unknown[]): ApiDataState<T> {
  const [state, setState] = useState<ApiDataState<T>>({ data: null, loading: true, error: null, errorStatus: null });
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    setState((s) => ({ ...s, loading: true, error: null, errorStatus: null }));
    fetcher()
      .then((data) => {
        if (requestId.current === id) setState({ data, loading: false, error: null, errorStatus: null });
      })
      .catch((err: Error) => {
        if (requestId.current === id) {
          setState({ data: null, loading: false, error: err.message, errorStatus: err instanceof ApiError ? err.status : null });
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
