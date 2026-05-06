"""
Behavioural contract tests for KnowledgeStore implementations.

The `store` fixture in conftest.py is parametrized over InMemoryKnowledgeStore
and SqliteKnowledgeStore, so every test here runs against both backends.
"""
import pytest


# --- is_novel ---

async def test_is_novel_for_unseen_concept(store):
    assert await store.is_novel("decorator") is True


async def test_is_novel_false_when_confidence_at_default_cap(store):
    await store.upsert("decorator")
    # upsert sets confidence to 0.3; update x3 brings it to 0.9 (>= 0.8 cap)
    for _ in range(3):
        await store.update("decorator", understood=True)
    assert await store.is_novel("decorator") is False


async def test_is_novel_true_when_confidence_below_cap(store):
    await store.upsert("decorator")
    # confidence is 0.3 after upsert — below default cap of 0.8
    assert await store.is_novel("decorator") is True


async def test_is_novel_respects_custom_cap(store):
    await store.upsert("decorator")
    # confidence = 0.3; custom cap = 0.2 → not novel
    assert await store.is_novel("decorator", novel_if_confidence_below=0.2) is False
    # custom cap = 0.5 → still novel
    assert await store.is_novel("decorator", novel_if_confidence_below=0.5) is True


# --- get_confidence ---

async def test_get_confidence_returns_zero_for_unseen(store):
    assert await store.get_confidence("unknown") == pytest.approx(0.0)


async def test_get_confidence_returns_initial_value_after_upsert(store):
    await store.upsert("decorator")
    assert await store.get_confidence("decorator") == pytest.approx(0.3)


# --- upsert ---

async def test_upsert_creates_concept_at_initial_confidence(store):
    await store.upsert("lambda")
    assert await store.get_confidence("lambda") == pytest.approx(0.3)


async def test_upsert_second_call_increments_seen_count(store):
    await store.upsert("lambda")
    await store.upsert("lambda")
    rows = await store.all()
    row = next(r for r in rows if r["id"] == "lambda")
    assert row["seen_count"] == 2


async def test_upsert_second_call_does_not_change_confidence(store):
    await store.upsert("lambda")
    await store.upsert("lambda")
    assert await store.get_confidence("lambda") == pytest.approx(0.3)


# --- update ---

async def test_update_understood_increases_confidence(store):
    await store.upsert("decorator")
    result = await store.update("decorator", understood=True)
    assert result["confidence"] == pytest.approx(0.5)


async def test_update_not_understood_decreases_confidence(store):
    await store.upsert("decorator")
    result = await store.update("decorator", understood=False)
    assert result["confidence"] == pytest.approx(0.2)


async def test_update_clamps_at_upper_bound(store):
    await store.upsert("decorator")
    for _ in range(10):
        await store.update("decorator", understood=True)
    assert await store.get_confidence("decorator") == pytest.approx(1.0)


async def test_update_clamps_at_lower_bound(store):
    await store.upsert("decorator")
    for _ in range(10):
        await store.update("decorator", understood=False)
    assert await store.get_confidence("decorator") == pytest.approx(0.0)


async def test_update_missing_concept_returns_empty_dict(store):
    result = await store.update("nonexistent", understood=True)
    assert result == {}


# --- all ---

async def test_all_returns_empty_list_initially(store):
    assert await store.all() == []


async def test_all_returns_all_upserted_concepts(store):
    await store.upsert("decorator")
    await store.upsert("lambda")
    rows = await store.all()
    ids = {r["id"] for r in rows}
    assert ids == {"decorator", "lambda"}


# --- get_graph_state ---

async def test_get_graph_state_empty_store(store):
    gs = await store.get_graph_state()
    assert gs.total_seen == 0


async def test_get_graph_state_reflects_store_contents(store):
    await store.upsert("decorator")
    await store.upsert("lambda")
    gs = await store.get_graph_state()
    assert gs.total_seen == 2
    ids = {c.id for c in gs.concepts}
    assert ids == {"decorator", "lambda"}


# --- session_digest ---

async def test_session_digest_empty_store(store):
    digest = await store.session_digest()
    assert digest["concepts_seen"] == 0
    assert digest["new_concepts"] == []
    assert digest["gaps"] == []
