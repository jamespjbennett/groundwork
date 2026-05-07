import pytest
from unittest.mock import AsyncMock, patch

from explainer import ExplainerError, ExplanationResult
from memory_knowledge_store import InMemoryKnowledgeStore, _Row

_STUB = ExplanationResult(
    summary="Wrapped a method with @property.",
    explanation="A decorator wraps a function.",
    challenge_question="What does @property do?",
)

_DECORATOR_CODE = "@property\ndef x(self): pass"


def _payload(**overrides):
    base = {
        "code": _DECORATOR_CODE,
        "diff": "@@ -0,0 +1,2 @@\n+@property\n+def x(self): pass",
        "file_path": "api/main.py",
        "language": "python",
        "session_id": "sess-test",
    }
    base.update(overrides)
    return base


async def _seed_entry(store, **kw):
    """Insert one fully-formed entry against an InMemoryKnowledgeStore."""
    await store.upsert(kw.get("concept_id", "decorator"))
    return await store.record_entry(
        session_id=kw.get("session_id", "sess-test"),
        file_path=kw.get("file_path", "api/main.py"),
        language="python",
        origin="typed",
        diff="@@ ... @@",
        code_snippet=_DECORATOR_CODE,
        summary=kw.get("summary", "Added something."),
        explanation="long explanation",
        challenge_q="some question?",
        concepts=[(kw.get("concept_id", "decorator"), kw.get("is_novel", True))],
    )


# ---------- POST /analyse ----------

async def test_analyse_returns_slim_shape_for_novel_concept(api_client):
    client, _ = api_client
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        resp = await client.post("/analyse", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["skipped"] is False
    assert data["entry_id"]
    assert data["summary"] == _STUB.summary
    assert {"id", "name", "is_novel"} <= set(data["concepts"][0].keys())
    assert "explanation" not in data
    assert "challenge_question" not in data


async def test_analyse_persists_full_entry(api_client):
    client, store = api_client
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        resp = await client.post("/analyse", json=_payload())
    entry = await store.get_entry(resp.json()["entry_id"])
    assert entry["session_id"] == "sess-test"
    assert entry["file_path"] == "api/main.py"
    assert entry["explanation"] == _STUB.explanation


async def test_analyse_no_concepts_returns_skipped(api_client):
    client, _ = api_client
    resp = await client.post("/analyse", json=_payload(code="x = 1"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["skipped"] is True
    assert body["reason"] == "no_concepts"


async def test_analyse_already_known_concept_returns_skipped(api_client):
    client, store = api_client
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB) as mock_explain:
        resp = await client.post("/analyse", json=_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["skipped"] is True
    assert body["reason"] == "already_known"
    mock_explain.assert_not_called()


async def test_analyse_explainer_error_returns_503(api_client):
    client, _ = api_client
    with patch(
        "analyse_workflow.explain",
        new_callable=AsyncMock,
        side_effect=ExplainerError("model unavailable"),
    ):
        resp = await client.post("/analyse", json=_payload())
    assert resp.status_code == 503


async def test_analyse_rejects_payload_missing_required_field(api_client):
    client, _ = api_client
    for missing in ("session_id", "file_path", "diff", "code"):
        payload = _payload()
        del payload[missing]
        resp = await client.post("/analyse", json=payload)
        assert resp.status_code == 422, f"expected 422 when {missing} is missing"


# ---------- GET /concepts ----------

async def test_get_concepts_empty_store(api_client):
    client, _ = api_client
    resp = await client.get("/concepts")
    assert resp.status_code == 200
    assert resp.json() == {"concepts": []}


async def test_get_concepts_returns_stored_concepts(api_client):
    client, store = api_client
    await store.upsert("decorator")
    resp = await client.get("/concepts")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["concepts"]]
    assert "decorator" in ids


# ---------- POST /concepts/:id/respond ----------

async def test_respond_concept_updates_confidence_and_returns_spec_shape(api_client):
    client, store = api_client
    await store.upsert("decorator")
    resp = await client.post("/concepts/decorator/respond", json={"understood": True})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"confidence", "depth_level"}
    assert body["confidence"] == pytest.approx(0.5)
    assert body["depth_level"] == 1


async def test_respond_concept_decreases_confidence_on_not_understood(api_client):
    client, store = api_client
    await store.upsert("decorator")
    resp = await client.post("/concepts/decorator/respond", json={"understood": False})
    assert resp.status_code == 200
    assert resp.json()["confidence"] == pytest.approx(0.2)


async def test_respond_unknown_concept_returns_404(api_client):
    client, _ = api_client
    resp = await client.post("/concepts/nonexistent/respond", json={"understood": True})
    assert resp.status_code == 404


# ---------- GET /feed ----------

async def test_get_feed_empty(api_client):
    client, _ = api_client
    resp = await client.get("/feed")
    assert resp.status_code == 200
    assert resp.json() == {"entries": []}


async def test_get_feed_returns_summary_shape_only(api_client):
    client, store = api_client
    await _seed_entry(store)
    resp = await client.get("/feed")
    entries = resp.json()["entries"]
    assert len(entries) == 1
    item = entries[0]
    assert set(item.keys()) == {"id", "created_at", "file_path", "summary", "concepts"}


async def test_get_feed_filters_by_session(api_client):
    client, store = api_client
    a = await _seed_entry(store, session_id="sess-a", summary="a")
    await _seed_entry(store, session_id="sess-b", summary="b")
    resp = await client.get("/feed", params={"session_id": "sess-a"})
    ids = [e["id"] for e in resp.json()["entries"]]
    assert ids == [a]


async def test_get_feed_filters_by_concept(api_client):
    client, store = api_client
    a = await _seed_entry(store, concept_id="decorator", summary="a")
    await store.upsert("lambda")
    await _seed_entry(store, concept_id="lambda", summary="b")
    resp = await client.get("/feed", params={"concept_id": "decorator"})
    ids = [e["id"] for e in resp.json()["entries"]]
    assert ids == [a]


async def test_get_feed_respects_limit(api_client):
    client, store = api_client
    for i in range(5):
        await _seed_entry(store, summary=f"e{i}")
    resp = await client.get("/feed", params={"limit": 2})
    assert len(resp.json()["entries"]) == 2


# ---------- GET /feed/:id ----------

async def test_get_feed_entry_returns_full_record(api_client):
    client, store = api_client
    entry_id = await _seed_entry(store)
    resp = await client.get(f"/feed/{entry_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == entry_id
    # heavy fields are exposed via the detail endpoint
    assert body["explanation"] == "long explanation"
    assert body["diff"]
    assert body["code_snippet"]
    assert body["challenge_q"]


async def test_get_feed_entry_returns_404_for_missing(api_client):
    client, _ = api_client
    resp = await client.get("/feed/does-not-exist")
    assert resp.status_code == 404


# ---------- GET /digest ----------

async def test_get_digest_empty_store(api_client):
    client, _ = api_client
    resp = await client.get("/digest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_count"] == 0
    assert body["files_touched"] == []
    assert body["new_concepts"] == []
    assert body["reinforced_concepts"] == []
    assert body["fading_concepts"] == []
    assert body["unanswered_challenges"] == 0


async def test_get_digest_summarises_today(api_client):
    client, store = api_client
    await _seed_entry(store, file_path="a.py", session_id="s1")
    await _seed_entry(store, file_path="b.py", session_id="s1")
    resp = await client.get("/digest")
    body = resp.json()
    assert body["session_count"] == 1
    assert sorted(body["files_touched"]) == ["a.py", "b.py"]
    assert {c["id"] for c in body["new_concepts"]} == {"decorator"}


async def test_get_digest_rejects_invalid_date(api_client):
    client, _ = api_client
    resp = await client.get("/digest", params={"date": "not-a-date"})
    assert resp.status_code == 422
