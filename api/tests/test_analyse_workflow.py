import pytest
from unittest.mock import AsyncMock, patch

from analyse_workflow import analyse_submission
from explainer import ExplainerError, ExplanationResult
from memory_knowledge_store import InMemoryKnowledgeStore, _Row

_STUB = ExplanationResult(
    explanation="A decorator wraps a function.",
    challenge_question="What does @property do?",
)

_DECORATOR_CODE = "@property\ndef x(self): pass"


@pytest.fixture
def store():
    return InMemoryKnowledgeStore()


async def test_novel_concept_returns_full_result(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        result = await analyse_submission(_DECORATOR_CODE, store)

    assert result["skipped"] is False
    assert "decorator" in result["concepts"]
    assert result["novel_concept"] == "decorator"
    assert result["explanation"] == _STUB.explanation
    assert result["challenge_question"] == _STUB.challenge_question


async def test_no_concepts_returns_skipped(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB) as mock_explain:
        result = await analyse_submission("x = 1 + 2", store)

    assert result["skipped"] is True
    assert result["reason"] == "already_known"
    mock_explain.assert_not_called()


async def test_already_known_concept_returns_skipped(store):
    # Push decorator confidence above the typed cap (0.8)
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.9, seen_count=5, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB) as mock_explain:
        result = await analyse_submission(_DECORATOR_CODE, store)

    assert result["skipped"] is True
    mock_explain.assert_not_called()


async def test_ai_generated_origin_uses_higher_cap(store):
    # Confidence 0.85: above typed cap (0.8) but below ai_generated cap (0.95)
    store._rows["decorator"] = _Row(
        id="decorator", name="decorator", confidence=0.85, seen_count=3, last_seen="2026-01-01"
    )
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        typed_result = await analyse_submission(_DECORATOR_CODE, store, origin="typed")

    store._rows["decorator"].confidence = 0.85  # reset for second call
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        ai_result = await analyse_submission(_DECORATOR_CODE, store, origin="ai_generated")

    assert typed_result["skipped"] is True
    assert ai_result["skipped"] is False


async def test_explainer_error_propagates(store):
    with patch(
        "analyse_workflow.explain",
        new_callable=AsyncMock,
        side_effect=ExplainerError("API down"),
    ):
        with pytest.raises(ExplainerError, match="API down"):
            await analyse_submission(_DECORATOR_CODE, store)


async def test_upsert_called_after_successful_explain(store):
    with patch("analyse_workflow.explain", new_callable=AsyncMock, return_value=_STUB):
        await analyse_submission(_DECORATOR_CODE, store)

    # concept should now be in the store
    assert await store.get_confidence("decorator") == pytest.approx(0.3)
