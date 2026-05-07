import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from graph_state import GraphState
from knowledge_store import NOVEL_CONFIDENCE_CAP_TYPED, graph_state_from_rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id            TEXT PRIMARY KEY,
    created_at    TEXT NOT NULL,
    session_id    TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    language      TEXT NOT NULL,
    origin        TEXT NOT NULL,
    diff          TEXT NOT NULL,
    code_snippet  TEXT NOT NULL,
    summary       TEXT NOT NULL,
    explanation   TEXT NOT NULL,
    challenge_q   TEXT
);

CREATE TABLE IF NOT EXISTS concepts (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    first_seen    TEXT,
    last_seen     TEXT,
    seen_count    INTEGER NOT NULL DEFAULT 0,
    confidence    REAL NOT NULL DEFAULT 0.0,
    depth_level   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entry_concepts (
    entry_id      TEXT NOT NULL,
    concept_id    TEXT NOT NULL,
    is_novel      INTEGER NOT NULL,
    PRIMARY KEY (entry_id, concept_id),
    FOREIGN KEY (entry_id) REFERENCES entries(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entries_session     ON entries(session_id);
CREATE INDEX IF NOT EXISTS idx_entry_concepts_cid  ON entry_concepts(concept_id);
"""

_DEFAULT_DB_PATH = Path(__file__).parent / "db" / "groundwork.db"

_ENTRY_COLS = (
    "id",
    "created_at",
    "session_id",
    "file_path",
    "language",
    "origin",
    "diff",
    "code_snippet",
    "summary",
    "explanation",
    "challenge_q",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteKnowledgeStore:
    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or _DEFAULT_DB_PATH

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

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
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT confidence FROM concepts WHERE id = ?", (concept_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return True
                return row[0] < cap

    async def get_confidence(self, concept_id: str) -> float:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT confidence FROM concepts WHERE id = ?", (concept_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0.0

    async def upsert(self, concept_id: str, seen: bool = True) -> None:
        now = _now()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO concepts (id, name, first_seen, last_seen, seen_count, confidence, depth_level)
                VALUES (?, ?, ?, ?, 1, 0.3, 1)
                ON CONFLICT(id) DO UPDATE SET
                    seen_count = seen_count + 1,
                    last_seen  = excluded.last_seen
                """,
                (concept_id, concept_id, now, now),
            )
            await db.commit()

    async def update(self, concept_id: str, understood: bool) -> dict:
        delta = 0.2 if understood else -0.1
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE concepts
                SET confidence = MAX(0.0, MIN(1.0, confidence + ?))
                WHERE id = ?
                """,
                (delta, concept_id),
            )
            await db.commit()
            async with db.execute(
                "SELECT id, name, confidence, seen_count, last_seen, depth_level FROM concepts WHERE id = ?",
                (concept_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip(
                        ["id", "name", "confidence", "seen_count", "last_seen", "depth_level"], row
                    ))
                return {}

    async def all(self) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, name, confidence, seen_count, last_seen FROM concepts ORDER BY last_seen DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    dict(zip(["id", "name", "confidence", "seen_count", "last_seen"], row))
                    for row in rows
                ]

    async def get_graph_state(self) -> GraphState:
        return graph_state_from_rows(await self.all())

    async def session_digest(self) -> dict:
        # Legacy concept-only digest used by the existing /session/digest endpoint.
        # Step 4 will replace this with get_digest at the endpoint layer.
        async with aiosqlite.connect(self._db_path) as db:
            today = datetime.now(timezone.utc).date().isoformat()
            async with db.execute(
                "SELECT id, name, confidence FROM concepts WHERE last_seen >= ?", (today,)
            ) as cursor:
                seen_today = [
                    dict(zip(["id", "name", "confidence"], row))
                    for row in await cursor.fetchall()
                ]
            async with db.execute(
                "SELECT id, name, confidence FROM concepts WHERE confidence < 0.6 AND last_seen < ?",
                (today,),
            ) as cursor:
                gaps = [
                    dict(zip(["id", "name", "confidence"], row))
                    for row in await cursor.fetchall()
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
        """Persist one analysed code change and its concept links. Returns the new entry id.

        Caller must have upserted each concept first; this method only writes the entry row
        and the join rows. concepts is a list of (concept_id, is_novel) pairs.
        """
        entry_id = str(uuid.uuid4())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO entries (id, created_at, session_id, file_path, language, origin,
                                     diff, code_snippet, summary, explanation, challenge_q)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id, _now(), session_id, file_path, language, origin,
                    diff, code_snippet, summary, explanation, challenge_q,
                ),
            )
            for concept_id, is_novel in concepts:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO entry_concepts (entry_id, concept_id, is_novel)
                    VALUES (?, ?, ?)
                    """,
                    (entry_id, concept_id, 1 if is_novel else 0),
                )
            await db.commit()
        return entry_id

    async def get_entry(self, entry_id: str) -> dict | None:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                f"SELECT {', '.join(_ENTRY_COLS)} FROM entries WHERE id = ?", (entry_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                entry = dict(zip(_ENTRY_COLS, row))
            entry["concepts"] = await self._concepts_for_entry(db, entry_id)
        return entry

    async def get_feed(
        self,
        *,
        session_id: str | None = None,
        concept_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        params: list = []
        clauses: list[str] = []
        if session_id:
            clauses.append("e.session_id = ?")
            params.append(session_id)
        if concept_id:
            clauses.append("EXISTS (SELECT 1 FROM entry_concepts ec WHERE ec.entry_id = e.id AND ec.concept_id = ?)")
            params.append(concept_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                f"""
                SELECT id, created_at, file_path, summary
                FROM entries e
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ) as cursor:
                rows = await cursor.fetchall()
            entries = [
                {"id": r[0], "created_at": r[1], "file_path": r[2], "summary": r[3]}
                for r in rows
            ]
            for entry in entries:
                entry["concepts"] = await self._concepts_for_entry(db, entry["id"])
        return entries

    async def get_digest(self, date: str | None = None) -> dict:
        target = date or datetime.now(timezone.utc).date().isoformat()
        FADING = 0.6

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT DISTINCT session_id FROM entries WHERE substr(created_at, 1, 10) = ?",
                (target,),
            ) as cursor:
                sessions = [r[0] for r in await cursor.fetchall()]

            async with db.execute(
                "SELECT DISTINCT file_path FROM entries WHERE substr(created_at, 1, 10) = ? ORDER BY file_path",
                (target,),
            ) as cursor:
                files_touched = [r[0] for r in await cursor.fetchall()]

            async with db.execute(
                """
                SELECT c.id, c.name, c.confidence, MAX(ec.is_novel) AS any_novel
                FROM entry_concepts ec
                JOIN concepts c ON c.id = ec.concept_id
                JOIN entries  e ON e.id = ec.entry_id
                WHERE substr(e.created_at, 1, 10) = ?
                GROUP BY c.id, c.name, c.confidence
                """,
                (target,),
            ) as cursor:
                new_concepts: list[dict] = []
                reinforced_concepts: list[dict] = []
                for r in await cursor.fetchall():
                    item = {"id": r[0], "name": r[1], "confidence": r[2]}
                    (new_concepts if r[3] else reinforced_concepts).append(item)

            async with db.execute(
                """
                SELECT id, name, confidence
                FROM concepts
                WHERE confidence < ?
                  AND last_seen IS NOT NULL
                  AND date(last_seen) < date(?, '-7 days')
                """,
                (FADING, target),
            ) as cursor:
                fading = [
                    {"id": r[0], "name": r[1], "confidence": r[2]}
                    for r in await cursor.fetchall()
                ]

            async with db.execute(
                """
                SELECT COUNT(DISTINCT e.id)
                FROM entries e
                WHERE substr(e.created_at, 1, 10) = ?
                  AND e.challenge_q IS NOT NULL AND e.challenge_q != ''
                  AND NOT EXISTS (
                    SELECT 1 FROM entry_concepts ec
                    JOIN concepts c ON c.id = ec.concept_id
                    WHERE ec.entry_id = e.id AND c.confidence > 0.5
                  )
                """,
                (target,),
            ) as cursor:
                row = await cursor.fetchone()
                unanswered = row[0] if row else 0

        return {
            "date": target,
            "session_count": len(sessions),
            "files_touched": files_touched,
            "new_concepts": new_concepts,
            "reinforced_concepts": reinforced_concepts,
            "fading_concepts": fading,
            "unanswered_challenges": unanswered,
        }

    async def _concepts_for_entry(self, db: aiosqlite.Connection, entry_id: str) -> list[dict]:
        async with db.execute(
            """
            SELECT c.id, c.name, ec.is_novel
            FROM entry_concepts ec
            JOIN concepts c ON c.id = ec.concept_id
            WHERE ec.entry_id = ?
            ORDER BY c.id
            """,
            (entry_id,),
        ) as cursor:
            return [
                {"id": r[0], "name": r[1], "is_novel": bool(r[2])}
                for r in await cursor.fetchall()
            ]
