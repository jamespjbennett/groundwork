"""
Behavioural contract tests for the entries surface (v0.2).

The `store` fixture in conftest.py is parametrized over InMemoryKnowledgeStore
and SqliteKnowledgeStore, so every test here runs against both backends.
"""
from datetime import datetime, timedelta, timezone

import pytest


def _entry_kwargs(**overrides):
    base = {
        "session_id": "sess-1",
        "file_path": "api/main.py",
        "language": "python",
        "origin": "typed",
        "diff": "@@ ... @@",
        "code_snippet": "@app.get('/')\ndef root(): ...",
        "summary": "Added a root route",
        "explanation": "You used the @app.get decorator to register a handler...",
        "challenge_q": "What HTTP verb does @app.get bind to?",
        "concepts": [("decorator", True)],
    }
    base.update(overrides)
    return base


# --- record_entry ---

async def test_record_entry_returns_id(store):
    await store.upsert("decorator")
    entry_id = await store.record_entry(**_entry_kwargs())
    assert isinstance(entry_id, str)
    assert len(entry_id) > 0


async def test_record_entry_persists_full_record(store):
    await store.upsert("decorator")
    entry_id = await store.record_entry(**_entry_kwargs())
    entry = await store.get_entry(entry_id)

    assert entry is not None
    assert entry["id"] == entry_id
    assert entry["session_id"] == "sess-1"
    assert entry["file_path"] == "api/main.py"
    assert entry["language"] == "python"
    assert entry["origin"] == "typed"
    assert entry["summary"] == "Added a root route"
    assert "decorator" in entry["explanation"] or "@app.get" in entry["explanation"]
    assert entry["challenge_q"].endswith("?")


async def test_record_entry_links_concepts(store):
    await store.upsert("decorator")
    await store.upsert("type_annotation")
    entry_id = await store.record_entry(**_entry_kwargs(
        concepts=[("decorator", True), ("type_annotation", False)]
    ))
    entry = await store.get_entry(entry_id)

    by_id = {c["id"]: c for c in entry["concepts"]}
    assert by_id["decorator"]["is_novel"] is True
    assert by_id["type_annotation"]["is_novel"] is False


async def test_record_entry_with_no_concepts(store):
    entry_id = await store.record_entry(**_entry_kwargs(concepts=[]))
    entry = await store.get_entry(entry_id)
    assert entry["concepts"] == []


async def test_record_entry_allows_null_challenge(store):
    await store.upsert("decorator")
    entry_id = await store.record_entry(**_entry_kwargs(challenge_q=None))
    entry = await store.get_entry(entry_id)
    assert entry["challenge_q"] is None


# --- get_entry ---

async def test_get_entry_missing_returns_none(store):
    assert await store.get_entry("does-not-exist") is None


# --- get_feed ---

async def test_get_feed_empty(store):
    assert await store.get_feed() == []


async def test_get_feed_returns_summary_shape(store):
    await store.upsert("decorator")
    await store.record_entry(**_entry_kwargs())

    feed = await store.get_feed()
    assert len(feed) == 1
    item = feed[0]
    assert set(item.keys()) == {"id", "created_at", "file_path", "summary", "concepts"}
    # full explanation/diff/code_snippet must NOT leak into the feed list view
    assert "explanation" not in item
    assert "diff" not in item


async def test_get_feed_orders_newest_first(store):
    await store.upsert("decorator")
    first = await store.record_entry(**_entry_kwargs(summary="first"))
    second = await store.record_entry(**_entry_kwargs(summary="second"))

    feed = await store.get_feed()
    assert [e["summary"] for e in feed] == ["second", "first"]
    assert [e["id"] for e in feed] == [second, first]


async def test_get_feed_filters_by_session(store):
    await store.upsert("decorator")
    a = await store.record_entry(**_entry_kwargs(session_id="sess-a"))
    await store.record_entry(**_entry_kwargs(session_id="sess-b"))

    feed = await store.get_feed(session_id="sess-a")
    assert [e["id"] for e in feed] == [a]


async def test_get_feed_filters_by_concept(store):
    await store.upsert("decorator")
    await store.upsert("lambda")
    a = await store.record_entry(**_entry_kwargs(concepts=[("decorator", True)]))
    await store.record_entry(**_entry_kwargs(concepts=[("lambda", True)]))

    feed = await store.get_feed(concept_id="decorator")
    assert [e["id"] for e in feed] == [a]


async def test_get_feed_respects_limit(store):
    await store.upsert("decorator")
    for i in range(5):
        await store.record_entry(**_entry_kwargs(summary=f"e{i}"))

    feed = await store.get_feed(limit=2)
    assert len(feed) == 2


# --- get_digest ---

async def test_get_digest_empty(store):
    digest = await store.get_digest()
    assert digest["session_count"] == 0
    assert digest["files_touched"] == []
    assert digest["new_concepts"] == []
    assert digest["reinforced_concepts"] == []
    assert digest["fading_concepts"] == []
    assert digest["unanswered_challenges"] == 0


async def test_get_digest_counts_sessions_and_files(store):
    await store.upsert("decorator")
    await store.record_entry(**_entry_kwargs(session_id="s1", file_path="a.py"))
    await store.record_entry(**_entry_kwargs(session_id="s1", file_path="b.py"))
    await store.record_entry(**_entry_kwargs(session_id="s2", file_path="a.py"))

    digest = await store.get_digest()
    assert digest["session_count"] == 2
    assert digest["files_touched"] == ["a.py", "b.py"]


async def test_get_digest_groups_concepts_new_vs_reinforced(store):
    await store.upsert("decorator")
    await store.upsert("lambda")
    await store.record_entry(**_entry_kwargs(
        concepts=[("decorator", True), ("lambda", False)]
    ))

    digest = await store.get_digest()
    assert {c["id"] for c in digest["new_concepts"]} == {"decorator"}
    assert {c["id"] for c in digest["reinforced_concepts"]} == {"lambda"}


async def test_get_digest_unanswered_challenges_counts_low_confidence(store):
    await store.upsert("decorator")
    await store.record_entry(**_entry_kwargs())  # challenge_q is set, decorator confidence = 0.3

    digest = await store.get_digest()
    assert digest["unanswered_challenges"] == 1


async def test_get_digest_unanswered_challenges_excludes_high_confidence(store):
    await store.upsert("decorator")
    # Push confidence above the 0.5 cutoff used by the unanswered logic.
    for _ in range(2):
        await store.update("decorator", understood=True)
    await store.record_entry(**_entry_kwargs())

    digest = await store.get_digest()
    assert digest["unanswered_challenges"] == 0
