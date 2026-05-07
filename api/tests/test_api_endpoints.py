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


# --- GET /concepts ---

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


# --- GET /session/digest ---

async def test_get_session_digest_empty_store(api_client):
    client, _ = api_client
    resp = await client.get("/session/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["concepts_seen"] == 0
    assert data["new_concepts"] == []
    assert data["gaps"] == []


# --- POST /respond ---

async def test_respond_updates_known_concept(api_client):
    client, store = api_client
    await store.upsert("decorator")
    resp = await client.post("/respond", json={"concept_id": "decorator", "understood": True})
    assert resp.status_code == 200
    updated = resp.json()["updated_concept"]
    assert updated["id"] == "decorator"
    assert updated["confidence"] == pytest.approx(0.5)


async def test_respond_unknown_concept_returns_empty_dict(api_client):
    client, _ = api_client
    resp = await client.post("/respond", json={"concept_id": "nonexistent", "understood": True})
    assert resp.status_code == 200
    assert resp.json() == {"updated_concept": {}}


# --- POST /analyse ---

async def test_analyse_novel_concept_returns_explanation(api_client):
    client, _ = api_client
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        resp = await client.post("/analyse", json={"code": _DECORATOR_CODE, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["skipped"] is False
    assert data["novel_concept"] == "decorator"
    assert data["explanation"] == _STUB.explanation


async def test_analyse_empty_code_returns_skipped(api_client):
    client, _ = api_client
    resp = await client.post("/analyse", json={"code": "x = 1", "language": "python"})
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True


async def test_analyse_already_known_concept_returns_skipped(api_client):
    client, store = api_client
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB) as mock_explain:
        resp = await client.post("/analyse", json={"code": _DECORATOR_CODE, "language": "python"})
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True
    mock_explain.assert_not_called()


async def test_analyse_explainer_error_returns_503(api_client):
    client, _ = api_client
    with patch(
        "analyse_workflow.explain",
        new_callable=AsyncMock,
        side_effect=ExplainerError("model unavailable"),
    ):
        resp = await client.post("/analyse", json={"code": _DECORATOR_CODE, "language": "python"})
    assert resp.status_code == 503


async def test_analyse_ai_generated_origin_accepted(api_client):
    client, _ = api_client
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        resp = await client.post(
            "/analyse",
            json={"code": _DECORATOR_CODE, "language": "python", "origin": "ai_generated"},
        )
    assert resp.status_code == 200
    assert resp.json()["skipped"] is False
