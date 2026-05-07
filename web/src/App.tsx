import { useEffect, useState } from "react";

import { ApiError, api } from "./api";
import type { FeedItem } from "./types";

type State =
  | { kind: "loading" }
  | { kind: "ok"; entries: FeedItem[] }
  | { kind: "error"; message: string };

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    api
      .feed()
      .then((r) => setState({ kind: "ok", entries: r.entries }))
      .catch((e: unknown) => {
        const message =
          e instanceof ApiError
            ? `${e.message} — is the API running on :8000?`
            : String(e);
        setState({ kind: "error", message });
      });
  }, []);

  return (
    <main style={{ padding: 32, maxWidth: 880, margin: "0 auto" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.25rem", margin: 0 }}>Groundwork</h1>
        <p style={{ margin: "4px 0 0", opacity: 0.6, fontSize: "0.85rem" }}>
          A coding journal with understanding baked in.
        </p>
      </header>

      {state.kind === "loading" && <p>Loading…</p>}

      {state.kind === "error" && (
        <p style={{ color: "#ff8a8a" }}>Error: {state.message}</p>
      )}

      {state.kind === "ok" && (
        <p>
          {state.entries.length === 0
            ? "No entries yet — save a Python file in your editor."
            : `${state.entries.length} ${
                state.entries.length === 1 ? "entry" : "entries"
              } in the feed. (Step 7 will render them.)`}
        </p>
      )}
    </main>
  );
}
