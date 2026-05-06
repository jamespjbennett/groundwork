from dataclasses import dataclass, field
from datetime import datetime, timezone

from graph_state import GraphState
from knowledge_store import NOVEL_CONFIDENCE_CAP_TYPED, graph_state_from_rows


@dataclass
class _Row:
    id: str
    name: str
    confidence: float
    seen_count: int
    last_seen: str | None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "confidence": self.confidence,
            "seen_count": self.seen_count,
            "last_seen": self.last_seen,
        }


@dataclass
class InMemoryKnowledgeStore:
    """SQLite-free adapter for tests and experiments."""

    _rows: dict[str, _Row] = field(default_factory=dict)

    async def init(self) -> None:
        return None

    async def is_novel(
        self,
        concept_id: str,
        *,
        novel_if_confidence_below: float | None = None,
    ) -> bool:
        cap = (
            novel_if_confidence_below
            if novel_if_confidence_below is not None
            else NOVEL_CONFIDENCE_CAP_TYPED
        )
        row = self._rows.get(concept_id)
        if row is None:
            return True
        return row.confidence < cap

    async def get_confidence(self, concept_id: str) -> float:
        row = self._rows.get(concept_id)
        return row.confidence if row else 0.0

    async def upsert(self, concept_id: str, seen: bool = True) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if concept_id not in self._rows:
            self._rows[concept_id] = _Row(
                id=concept_id,
                name=concept_id,
                confidence=0.3,
                seen_count=1,
                last_seen=now,
            )
        else:
            r = self._rows[concept_id]
            r.seen_count += 1
            r.last_seen = now

    async def update(self, concept_id: str, understood: bool) -> dict:
        delta = 0.2 if understood else -0.1
        row = self._rows.get(concept_id)
        if not row:
            return {}
        row.confidence = max(0.0, min(1.0, row.confidence + delta))
        return {
            "id": row.id,
            "name": row.name,
            "confidence": row.confidence,
            "seen_count": row.seen_count,
            "last_seen": row.last_seen,
        }

    async def all(self) -> list[dict]:
        ordered = sorted(
            self._rows.values(),
            key=lambda r: r.last_seen or "",
            reverse=True,
        )
        return [r.as_dict() for r in ordered]

    async def get_graph_state(self) -> GraphState:
        return graph_state_from_rows(await self.all())

    async def session_digest(self) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        rows = await self.all()
        seen_today = []
        for r in rows:
            ls = r.get("last_seen")
            if ls and ls >= today:
                seen_today.append(
                    {"id": r["id"], "name": r["name"], "confidence": r["confidence"]}
                )
        gaps = []
        for r in rows:
            ls = r.get("last_seen")
            if r["confidence"] < 0.6 and ls and ls < today:
                gaps.append(
                    {"id": r["id"], "name": r["name"], "confidence": r["confidence"]}
                )
        new_concepts = [c for c in seen_today if c["confidence"] <= 0.3]
        return {"concepts_seen": len(seen_today), "new_concepts": new_concepts, "gaps": gaps}
