import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "groundwork.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS concepts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 0.0,
    seen_count  INTEGER NOT NULL DEFAULT 0,
    last_seen   TEXT
);
"""

NOVEL_THRESHOLD = 0.8


class KnowledgeGraph:
    async def init(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(SCHEMA)
            await db.commit()

    async def is_novel(self, concept_id: str) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT confidence FROM concepts WHERE id = ?", (concept_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return True
                return row[0] < NOVEL_THRESHOLD

    async def get_confidence(self, concept_id: str) -> float:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT confidence FROM concepts WHERE id = ?", (concept_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0.0

    async def upsert(self, concept_id: str, seen: bool = True):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO concepts (id, name, confidence, seen_count, last_seen)
                VALUES (?, ?, 0.3, 1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    seen_count = seen_count + 1,
                    last_seen = excluded.last_seen
                """,
                (concept_id, concept_id, now),
            )
            await db.commit()

    async def update(self, concept_id: str, understood: bool) -> dict:
        delta = 0.2 if understood else -0.1
        async with aiosqlite.connect(DB_PATH) as db:
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
                "SELECT id, name, confidence, seen_count, last_seen FROM concepts WHERE id = ?",
                (concept_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip(["id", "name", "confidence", "seen_count", "last_seen"], row))
                return {}

    async def all(self) -> list[dict]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, confidence, seen_count, last_seen FROM concepts ORDER BY last_seen DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    dict(zip(["id", "name", "confidence", "seen_count", "last_seen"], row))
                    for row in rows
                ]

    async def get_graph_state(self) -> dict:
        concepts = await self.all()
        return {
            "total_seen": len(concepts),
            "avg_confidence": sum(c["confidence"] for c in concepts) / max(len(concepts), 1),
            "concepts": concepts,
        }

    async def session_digest(self) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
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
