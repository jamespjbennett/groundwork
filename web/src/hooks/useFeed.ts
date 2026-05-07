import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api";
import type { FeedItem } from "../types";

const POLL_MS = 10_000;

export interface FeedState {
  entries: FeedItem[] | null;
  error: string | null;
  loading: boolean;
}

// Polls GET /feed every POLL_MS. On a transient error we keep the last
// known entries on screen so the UI doesn't flicker — only the error
// banner reflects the failure.
export function useFeed(): FeedState {
  const [state, setState] = useState<FeedState>({
    entries: null,
    error: null,
    loading: true,
  });
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;

    async function tick() {
      try {
        const r = await api.feed();
        if (cancelled.current) return;
        setState({ entries: r.entries, error: null, loading: false });
      } catch (e: unknown) {
        if (cancelled.current) return;
        const message = e instanceof ApiError ? e.message : String(e);
        setState((prev) => ({
          entries: prev.entries,
          error: message,
          loading: false,
        }));
      }
    }

    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled.current = true;
      clearInterval(id);
    };
  }, []);

  return state;
}
