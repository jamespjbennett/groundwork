import { useState } from "react";

import { useEntry } from "../hooks/useEntry";
import type { FeedItem } from "../types";
import { CodeBlock } from "./CodeBlock";
import { ConceptBadge } from "./ConceptBadge";
import { Explanation } from "./Explanation";

export function EntryCard({ item }: { item: FeedItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="card">
      <button
        type="button"
        className="card__button"
        onClick={() => setExpanded((x) => !x)}
        aria-expanded={expanded}
      >
        <div className="card__head">
          <code className="mono card__path">{item.file_path}</code>
          <time className="card__time">{formatTime(item.created_at)}</time>
        </div>
        <div className="card__summary">{item.summary}</div>
        <div className="card__badges">
          {item.concepts.map((c) => (
            <ConceptBadge key={c.id} concept={c} />
          ))}
        </div>
      </button>

      {expanded && (
        <div className="card__detail">
          <ExpandedDetail entryId={item.id} />
        </div>
      )}
    </article>
  );
}

function ExpandedDetail({ entryId }: { entryId: string }) {
  const state = useEntry(entryId);

  if (state.kind === "loading") {
    return <div className="muted">Loading detail…</div>;
  }
  if (state.kind === "error") {
    return <div className="error-banner">Error: {state.message}</div>;
  }

  const { entry } = state;
  return (
    <>
      <CodeBlock code={entry.code_snippet} language={entry.language} />
      <Explanation text={entry.explanation} />
      {entry.challenge_q && (
        <div className="challenge">
          <div className="challenge__label">Challenge</div>
          <div className="challenge__text">{entry.challenge_q}</div>
        </div>
      )}
    </>
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
