import pytest
from unittest.mock import AsyncMock, patch

from analyse_workflow import analyse_submission
from explainer import ExplainerError, ExplanationResult
from memory_knowledge_store import InMemoryKnowledgeStore, _Row

_STUB = ExplanationResult(
    summary="Wrapped a method with @property.",
    explanation="A decorator wraps a function.",
    challenge_question="What does @property do?",
)

_DECORATOR_CODE = "@property\ndef x(self): pass"


def _kwargs(**overrides):
    base = {
        "code": _DECORATOR_CODE,
        "diff": "@@ -0,0 +1,2 @@\n+@property\n+def x(self): pass",
        "file_path": "api/main.py",
        "session_id": "sess-test",
    }
    base.update(overrides)
    return base


@pytest.fixture
def store():
    return InMemoryKnowledgeStore()


# --- novel concept happy path ---

async def test_novel_concept_returns_slim_shape(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        result = await analyse_submission(**_kwargs(), knowledge=store)

    assert result["skipped"] is False
    assert result["entry_id"]
    assert result["summary"] == _STUB.summary
    assert {"id", "name", "is_novel"} <= set(result["concepts"][0].keys())
    # explanation/challenge are stored in the DB, not echoed in the response
    assert "explanation" not in result
    assert "challenge_question" not in result


async def test_novel_concept_persists_full_entry(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        result = await analyse_submission(**_kwargs(), knowledge=store)

    entry = await store.get_entry(result["entry_id"])
    assert entry["session_id"] == "sess-test"
    assert entry["file_path"] == "api/main.py"
    assert entry["origin"] == "typed"
    assert entry["language"] == "python"
    assert entry["diff"].startswith("@@")
    assert entry["code_snippet"] == _DECORATOR_CODE
    assert entry["summary"] == _STUB.summary
    assert entry["explanation"] == _STUB.explanation
    assert entry["challenge_q"] == _STUB.challenge_question


async def test_novel_concept_marks_concept_as_novel_in_join(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        result = await analyse_submission(**_kwargs(), knowledge=store)

    by_id = {c["id"]: c for c in result["concepts"]}
    assert by_id["decorator"]["is_novel"] is True


async def test_explain_called_with_file_path(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB) as mock:
        await analyse_submission(**_kwargs(file_path="path/x.py"), knowledge=store)
    _, kwargs = mock.call_args
    assert kwargs["file_path"] == "path/x.py"


# --- skip paths ---

async def test_no_concepts_returns_skipped_with_reason(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock) as mock_explain:
        result = await analyse_submission(**_kwargs(code="x = 1 + 2"), knowledge=store)

    assert result["skipped"] is True
    assert result["reason"] == "no_concepts"
    assert result["concepts"] == []
    mock_explain.assert_not_called()


async def test_already_known_concepts_returns_skipped(store):
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock) as mock_explain:
        result = await analyse_submission(**_kwargs(), knowledge=store)

    assert result["skipped"] is True
    assert result["reason"] == "already_known"
    assert any(c["id"] == "decorator" for c in result["concepts"])
    mock_explain.assert_not_called()


async def test_skip_path_does_not_record_entry(store):
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock):
        await analyse_submission(**_kwargs(), knowledge=store)
    assert await store.get_feed() == []


# --- mixed novel + reinforced ---

async def test_mixed_concepts_flag_correctly_in_entry(store):
    store._rows["lambda"] = _Row(
        id="lambda", name="lambda", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    code_with_both = "@property\ndef f(): return lambda x: x"

    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        result = await analyse_submission(**_kwargs(code=code_with_both), knowledge=store)

    by_id = {c["id"]: c for c in result["concepts"]}
    assert by_id["decorator"]["is_novel"] is True
    assert by_id["lambda"]["is_novel"] is False


async def test_reinforced_concepts_have_seen_count_incremented(store):
    store._rows["lambda"] = _Row(
        id="lambda", name="lambda", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    code_with_both = "@property\ndef f(): return lambda x: x"

    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        await analyse_submission(**_kwargs(code=code_with_both), knowledge=store)

    assert store._rows["lambda"].seen_count == 6


# --- origin handling ---

async def test_ai_generated_origin_uses_higher_cap(store):
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.85, seen_count=3, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        typed = await analyse_submission(**_kwargs(origin="typed"), knowledge=store)

    store._rows["decorator"].confidence = 0.85
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        ai = await analyse_submission(**_kwargs(origin="ai_generated"), knowledge=store)

    assert typed["skipped"] is True
    assert ai["skipped"] is False


# --- error propagation ---

async def test_explainer_error_propagates(store):
    with patch(
        "analyse_workflow.explain",
        new_callable=AsyncMock,
        side_effect=ExplainerError("API down"),
    ):
        with pytest.raises(ExplainerError, match="API down"):
            await analyse_submission(**_kwargs(), knowledge=store)


async def test_explainer_error_does_not_record_entry(store):
    with patch(
        "analyse_workflow.explain",
        new_callable=AsyncMock,
        side_effect=ExplainerError("API down"),
    ):
        with pytest.raises(ExplainerError):
            await analyse_submission(**_kwargs(), knowledge=store)
    assert await store.get_feed() == []
