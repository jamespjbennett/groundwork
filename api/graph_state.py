from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptRecord:
    """One row from the learner's concept store (for snapshot / calibration context)."""

    id: str
    name: str
    confidence: float
    seen_count: int
    last_seen: str | None

    @staticmethod
    def from_store(row: dict) -> ConceptRecord:
        return ConceptRecord(
            id=row["id"],
            name=row["name"],
            confidence=float(row["confidence"]),
            seen_count=int(row["seen_count"]),
            last_seen=row["last_seen"],
        )


@dataclass(frozen=True)
class GraphState:
    """Read model passed into depth calibration (and future explainer context)."""

    concepts: tuple[ConceptRecord, ...]

    @property
    def total_seen(self) -> int:
        return len(self.concepts)

    @property
    def avg_confidence(self) -> float:
        if not self.concepts:
            return 0.0
        return sum(c.confidence for c in self.concepts) / len(self.concepts)
