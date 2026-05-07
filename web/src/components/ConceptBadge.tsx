import type { ResultConcept } from "../types";

// Minimal badge — novel concepts pop in blue, reinforced ones sit muted.
// Step 8 will refine the visual language alongside the code-block component.
export function ConceptBadge({ concept }: { concept: ResultConcept }) {
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: "0.7rem",
        background: concept.is_novel ? "#172a44" : "#15171c",
        color: concept.is_novel ? "#82b1ff" : "#9aa0a8",
        border: `1px solid ${concept.is_novel ? "#2a4d7d" : "#22252b"}`,
      }}
    >
      {concept.name}
      {concept.is_novel && (
        <span style={{ opacity: 0.7, fontSize: "0.65rem" }}>· new</span>
      )}
    </span>
  );
}
