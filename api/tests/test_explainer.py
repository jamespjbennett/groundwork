"""Integration-ish tests for explain() — prompt construction and retry behaviour.

The Anthropic client is patched out at the _call_model boundary so these tests
never make real network calls.
"""
from unittest.mock import AsyncMock, patch

import pytest

import explainer
from explainer import ExplainerError, explain
from graph_state import GraphState


_EMPTY_GRAPH = GraphState(())

_GOOD_RESPONSE = (
    '{"summary": "Added a class for DB connections.",'
    ' "explanation": "Wraps setup/teardown via __enter__/__exit__.",'
    ' "challenge_q": "What does __exit__ return?"}'
)


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


# --- happy path ---

async def test_explain_returns_all_three_fields():
    with patch("explainer._call_model", new_callable=AsyncMock, return_value=_GOOD_RESPONSE):
        result = await explain("decorator", "@property\ndef x(self): pass", _EMPTY_GRAPH)
    assert result.summary == "Added a class for DB connections."
    assert result.explanation == "Wraps setup/teardown via __enter__/__exit__."
    assert result.challenge_question == "What does __exit__ return?"


async def test_explain_passes_concept_and_code_into_prompt():
    captured: list[str] = []

    async def _capture(prompt: str) -> str:
        captured.append(prompt)
        return _GOOD_RESPONSE

    with patch("explainer._call_model", new=_capture):
        await explain("decorator", "@app.get('/')\ndef root(): ...", _EMPTY_GRAPH)

    prompt = captured[0]
    assert "decorator" in prompt
    assert "@app.get" in prompt


async def test_explain_includes_file_path_when_provided():
    captured: list[str] = []

    async def _capture(prompt: str) -> str:
        captured.append(prompt)
        return _GOOD_RESPONSE

    with patch("explainer._call_model", new=_capture):
        await explain(
            "decorator",
            "@app.get('/')\ndef root(): ...",
            _EMPTY_GRAPH,
            file_path="api/main.py",
        )

    assert "api/main.py" in captured[0]


# --- guard ---

async def test_explain_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ExplainerError, match="ANTHROPIC_API_KEY"):
        await explain("decorator", "code", _EMPTY_GRAPH)


# --- retry on bad output ---

async def test_explain_retries_once_when_first_response_is_invalid_json():
    responses = iter(["not json at all", _GOOD_RESPONSE])

    async def _two_step(prompt: str) -> str:
        return next(responses)

    with patch("explainer._call_model", new=_two_step):
        result = await explain("decorator", "code", _EMPTY_GRAPH)
    assert result.summary == "Added a class for DB connections."


async def test_explain_retry_prompt_contains_format_reminder():
    captured: list[str] = []

    async def _two_step(prompt: str) -> str:
        captured.append(prompt)
        return "garbage" if len(captured) == 1 else _GOOD_RESPONSE

    with patch("explainer._call_model", new=_two_step):
        await explain("decorator", "code", _EMPTY_GRAPH)

    assert len(captured) == 2
    # second prompt must reinforce the JSON shape
    assert "challenge_q" in captured[1]
    assert "ONLY" in captured[1] or "only" in captured[1]


async def test_explain_propagates_when_retry_also_fails():
    async def _always_bad(prompt: str) -> str:
        return "still not json"

    with patch("explainer._call_model", new=_always_bad):
        with pytest.raises(ExplainerError):
            await explain("decorator", "code", _EMPTY_GRAPH)


async def test_explain_does_not_retry_on_api_error():
    calls = 0

    async def _api_error(prompt: str) -> str:
        nonlocal calls
        calls += 1
        raise ExplainerError("network error")

    with patch("explainer._call_model", new=_api_error):
        with pytest.raises(ExplainerError, match="network error"):
            await explain("decorator", "code", _EMPTY_GRAPH)

    assert calls == 1
