import type { ResultConcept } from "../types";

export function ConceptBadge({ concept }: { concept: ResultConcept }) {
  return (
    <span className={`badge ${concept.is_novel ? "badge--novel" : "badge--seen"}`}>
      {concept.name}
      {concept.is_novel && <span className="badge__tag">· new</span>}
    </span>
  );
}
