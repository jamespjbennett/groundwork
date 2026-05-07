import { useState } from "react";

import { useEntry } from "../hooks/useEntry";
import type { FeedItem } from "../types";
import { ConceptBadge } from "./ConceptBadge";

export function EntryCard({ item }: { item: FeedItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article
      style={{
        background: "#13151a",
        border: "1px solid #1f2229",
        borderRadius: 8,
        marginBottom: 12,
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((x) => !x)}
        aria-expanded={expanded}
        style={{
          all: "unset",
          display: "block",
          width: "100%",
          padding: 16,
          cursor: "pointer",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 16,
            marginBottom: 8,
          }}
        >
          <code
            className="mono"
            style={{ color: "#9ca3af", fontSize: "0.78rem" }}
          >
            {item.file_path}
          </code>
          <time
            style={{
              color: "#6b7280",
              fontSize: "0.72rem",
              flexShrink: 0,
            }}
          >
            {formatTime(item.created_at)}
          </time>
        </div>
        <div style={{ fontWeight: 500, marginBottom: 10 }}>{item.summary}</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {item.concepts.map((c) => (
            <ConceptBadge key={c.id} concept={c} />
          ))}
        </div>
      </button>

      {expanded && (
        <div style={{ borderTop: "1px solid #1f2229", padding: 16 }}>
          <ExpandedDetail entryId={item.id} />
        </div>
      )}
    </article>
  );
}

function ExpandedDetail({ entryId }: { entryId: string }) {
  const state = useEntry(entryId);

  if (state.kind === "loading") {
    return <div style={{ opacity: 0.6 }}>Loading detail…</div>;
  }
  if (state.kind === "error") {
    return <div style={{ color: "#ff8a8a" }}>Error: {state.message}</div>;
  }

  const { entry } = state;
  return (
    <div>
      <pre
        className="mono"
        style={{
          background: "#0a0b0e",
          color: "#d4d6db",
          padding: 12,
          borderRadius: 6,
          overflow: "auto",
          fontSize: "0.82rem",
          marginTop: 0,
          marginBottom: 14,
          lineHeight: 1.5,
        }}
      >
        {entry.code_snippet}
      </pre>
      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
        {entry.explanation}
      </div>
      {entry.challenge_q && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "#161922",
            borderLeft: "3px solid #5b8def",
            borderRadius: 4,
          }}
        >
          <div
            style={{
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "#6b7280",
              marginBottom: 4,
            }}
          >
            Challenge
          </div>
          <div>{entry.challenge_q}</div>
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
