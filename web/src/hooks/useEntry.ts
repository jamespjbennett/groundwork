import { useEffect, useState } from "react";

import { ApiError, api } from "../api";
import type { Entry } from "../types";

export type EntryState =
  | { kind: "loading" }
  | { kind: "ok"; entry: Entry }
  | { kind: "error"; message: string };

// Lazily fetches one entry's full detail. The feed list view is slim
// by design (no explanation/diff/snippet), so we hit GET /feed/:id only
// when a card is expanded.
export function useEntry(id: string | null): EntryState {
  const [state, setState] = useState<EntryState>({ kind: "loading" });

  useEffect(() => {
    if (id === null) return;
    let cancelled = false;
    setState({ kind: "loading" });

    api
      .entry(id)
      .then((entry) => {
        if (!cancelled) setState({ kind: "ok", entry });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const message = e instanceof ApiError ? e.message : String(e);
        setState({ kind: "error", message });
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  return state;
}
