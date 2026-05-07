import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from graph_state import GraphState
from knowledge_store import NOVEL_CONFIDENCE_CAP_TYPED, graph_state_from_rows


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _Row:
    id: str
    name: str
    confidence: float
    seen_count: int
    last_seen: str | None
    first_seen: str | None = None
    depth_level: int = 1

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "confidence": self.confidence,
            "seen_count": self.seen_count,
            "last_seen": self.last_seen,
            "depth_level": self.depth_level,
        }


@dataclass
class _Entry:
    id: str
    created_at: str
    session_id: str
    file_path: str
    language: str
    origin: str
    diff: str
    code_snippet: str
    summary: str
    explanation: str
    challenge_q: str | None


@dataclass
class _EntryConcept:
    entry_id: str
    concept_id: str
    is_novel: bool


@dataclass
class InMemoryKnowledgeStore:
    """SQLite-free adapter for tests and experiments."""

    _rows: dict[str, _Row] = field(default_factory=dict)
    _entries: dict[str, _Entry] = field(default_factory=dict)
    _entry_concepts: list[_EntryConcept] = field(default_factory=list)

    async def init(self) -> None:
        return None

    # ---- concepts (existing) ----

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
        now = _now()
        if concept_id not in self._rows:
            self._rows[concept_id] = _Row(
                id=concept_id,
                name=concept_id,
                confidence=0.3,
                seen_count=1,
                last_seen=now,
                first_seen=now,
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
        return row.as_dict()

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
        seen_today = [
            {"id": r["id"], "name": r["name"], "confidence": r["confidence"]}
            for r in rows
            if r.get("last_seen") and r["last_seen"] >= today
        ]
        gaps = [
            {"id": r["id"], "name": r["name"], "confidence": r["confidence"]}
            for r in rows
            if r["confidence"] < 0.6 and r.get("last_seen") and r["last_seen"] < today
        ]
        new_concepts = [c for c in seen_today if c["confidence"] <= 0.3]
        return {"concepts_seen": len(seen_today), "new_concepts": new_concepts, "gaps": gaps}

    # ---- entries (new) ----

    async def record_entry(
        self,
        *,
        session_id: str,
        file_path: str,
        language: str,
        origin: str,
        diff: str,
        code_snippet: str,
        summary: str,
        explanation: str,
        challenge_q: str | None,
        concepts: list[tuple[str, bool]],
    ) -> str:
        entry_id = str(uuid.uuid4())
        self._entries[entry_id] = _Entry(
            id=entry_id,
            created_at=_now(),
            session_id=session_id,
            file_path=file_path,
            language=language,
            origin=origin,
            diff=diff,
            code_snippet=code_snippet,
            summary=summary,
            explanation=explanation,
            challenge_q=challenge_q,
        )
        seen_pairs = set()
        for cid, is_novel in concepts:
            if (entry_id, cid) in seen_pairs:
                continue
            seen_pairs.add((entry_id, cid))
            self._entry_concepts.append(
                _EntryConcept(entry_id=entry_id, concept_id=cid, is_novel=bool(is_novel))
            )
        return entry_id

    async def get_entry(self, entry_id: str) -> dict | None:
        e = self._entries.get(entry_id)
        if not e:
            return None
        return {**e.__dict__, "concepts": self._concepts_for_entry(entry_id)}

    async def get_feed(
        self,
        *,
        session_id: str | None = None,
        concept_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        ids_with_concept: set[str] | None = None
        if concept_id:
            ids_with_concept = {ec.entry_id for ec in self._entry_concepts if ec.concept_id == concept_id}

        matched = [
            e for e in self._entries.values()
            if (session_id is None or e.session_id == session_id)
            and (ids_with_concept is None or e.id in ids_with_concept)
        ]
        matched.sort(key=lambda e: e.created_at, reverse=True)
        return [
            {
                "id": e.id,
                "created_at": e.created_at,
                "file_path": e.file_path,
                "summary": e.summary,
                "concepts": self._concepts_for_entry(e.id),
            }
            for e in matched[:limit]
        ]

    async def get_digest(self, date: str | None = None) -> dict:
        target = date or datetime.now(timezone.utc).date().isoformat()
        FADING = 0.6

        on_date = [e for e in self._entries.values() if e.created_at[:10] == target]
        sessions = {e.session_id for e in on_date}
        files_touched = sorted({e.file_path for e in on_date})

        # Group concepts referenced on this date as new vs reinforced.
        # A concept is considered "new" if any of its entries on this date had is_novel=True.
        novelty_by_concept: dict[str, bool] = {}
        for ec in self._entry_concepts:
            entry = self._entries.get(ec.entry_id)
            if not entry or entry.created_at[:10] != target:
                continue
            novelty_by_concept[ec.concept_id] = novelty_by_concept.get(ec.concept_id, False) or ec.is_novel

        new_concepts: list[dict] = []
        reinforced_concepts: list[dict] = []
        for cid, is_novel in novelty_by_concept.items():
            row = self._rows.get(cid)
            if not row:
                continue
            item = {"id": cid, "name": row.name, "confidence": row.confidence}
            (new_concepts if is_novel else reinforced_concepts).append(item)

        # Fading: confidence < threshold and last_seen older than 7 days from target.
        fading: list[dict] = []
        target_dt = datetime.fromisoformat(target)
        for r in self._rows.values():
            if r.confidence >= FADING or not r.last_seen:
                continue
            try:
                ls_dt = datetime.fromisoformat(r.last_seen[:10])
            except ValueError:
                continue
            if (target_dt - ls_dt).days > 7:
                fading.append({"id": r.id, "name": r.name, "confidence": r.confidence})

        # Unanswered challenges: entries on this date with a challenge_q
        # whose linked concepts are all still under 0.5 confidence.
        unanswered = 0
        for e in on_date:
            if not e.challenge_q:
                continue
            linked = [ec for ec in self._entry_concepts if ec.entry_id == e.id]
            if not linked:
                continue
            if all((self._rows.get(ec.concept_id) and self._rows[ec.concept_id].confidence <= 0.5) for ec in linked):
                unanswered += 1

        return {
            "date": target,
            "session_count": len(sessions),
            "files_touched": files_touched,
            "new_concepts": new_concepts,
            "reinforced_concepts": reinforced_concepts,
            "fading_concepts": fading,
            "unanswered_challenges": unanswered,
        }

    def _concepts_for_entry(self, entry_id: str) -> list[dict]:
        result = []
        for ec in self._entry_concepts:
            if ec.entry_id != entry_id:
                continue
            row = self._rows.get(ec.concept_id)
            name = row.name if row else ec.concept_id
            result.append({"id": ec.concept_id, "name": name, "is_novel": ec.is_novel})
        result.sort(key=lambda c: c["id"])
        return result
