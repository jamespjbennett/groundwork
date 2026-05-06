from typing import Literal, Protocol

from graph_state import ConceptRecord, GraphState

# Treat as "already known" when confidence >= cap; novel (explain) when confidence < cap.
NOVEL_CONFIDENCE_CAP_TYPED = 0.8
NOVEL_CONFIDENCE_CAP_AI_GENERATED = 0.95

NOVEL_THRESHOLD = NOVEL_CONFIDENCE_CAP_TYPED


def novelty_cap(origin: Literal["typed", "ai_generated"]) -> float:
    """Higher cap for AI/paste-shaped input — explain unless the learner is very confident."""
    if origin == "ai_generated":
        return NOVEL_CONFIDENCE_CAP_AI_GENERATED
    return NOVEL_CONFIDENCE_CAP_TYPED


class KnowledgeStore(Protocol):
    """External seam for persistence backing the learning loop."""

    async def init(self) -> None: ...
    async def is_novel(
        self,
        concept_id: str,
        *,
        novel_if_confidence_below: float | None = None,
    ) -> bool: ...
    async def get_confidence(self, concept_id: str) -> float: ...
    async def upsert(self, concept_id: str, seen: bool = True) -> None: ...
    async def update(self, concept_id: str, understood: bool) -> dict: ...
    async def all(self) -> list[dict]: ...
    async def get_graph_state(self) -> GraphState: ...
    async def session_digest(self) -> dict: ...


def graph_state_from_rows(rows: list[dict]) -> GraphState:
    return GraphState(tuple(ConceptRecord.from_store(r) for r in rows))
