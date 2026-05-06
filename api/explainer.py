import json
import os
from dataclasses import dataclass

import anthropic
import httpx

from depth_calibrator import calibrate_depth
from graph_state import GraphState

_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_DEPTH_INSTRUCTIONS = {
    "beginner": "Explain simply, avoid jargon, use an everyday analogy.",
    "intermediate": "Be concise. Assume basic Python knowledge. Skip trivial definitions.",
    "advanced": "Be precise and brief. Mention edge cases or internals if relevant.",
}


class ExplainerError(RuntimeError):
    """Raised when no structured explanation can be produced (API, empty output, or invalid JSON)."""


@dataclass(frozen=True)
class ExplanationResult:
    explanation: str
    challenge_question: str


async def explain(
    concept_id: str, code_snippet: str, graph_state: GraphState
) -> ExplanationResult:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ExplainerError("ANTHROPIC_API_KEY is not set")

    depth = calibrate_depth(graph_state)
    depth_instruction = _DEPTH_INSTRUCTIONS[depth]

    prompt = f"""You are a coding tutor embedded in a developer's editor.

The developer just wrote code containing the concept: **{concept_id}**.

Relevant code snippet:
```python
{code_snippet[:1000]}
```

Depth level: {depth}
Instruction: {depth_instruction}

Write a response with exactly two parts:
1. A 2–3 sentence explanation of this concept as it appears in the code above.
2. One challenge question that tests whether the developer understands it.

Format your response as JSON with keys "explanation" and "challenge_question". No other keys."""

    try:
        message = await _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise ExplainerError(f"Anthropic API error ({type(e).__name__}): {e}") from e
    except httpx.HTTPError as e:
        raise ExplainerError("Could not reach the explanation model (network error)") from e

    text = _message_to_text(message)
    return _parse_model_json(text)


def _message_to_text(message: object) -> str:
    content = getattr(message, "content", None)
    if not content:
        raise ExplainerError("Model returned no content")
    first = content[0]
    block = getattr(first, "text", None)
    if block is not None:
        return str(block).strip()
    if isinstance(first, dict) and first.get("type") == "text":
        return str(first.get("text", "")).strip()
    raise ExplainerError("Model response did not include a text block")


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    segments = text.split("```")
    inner = segments[1] if len(segments) > 1 else text
    inner = inner.strip()
    if inner.lower().startswith("json"):
        inner = inner[4:].lstrip()
    return inner.strip()


def _parse_model_json(text: str) -> ExplanationResult:
    stripped = _strip_json_fences(text)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise ExplainerError("Model response was not valid JSON") from e
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as e2:
            raise ExplainerError("Model response was not valid JSON") from e2

    if not isinstance(data, dict):
        raise ExplainerError("Model JSON was not an object")

    explanation = data.get("explanation")
    challenge_question = data.get("challenge_question")
    if not isinstance(explanation, str) or not isinstance(challenge_question, str):
        raise ExplainerError(
            'Model JSON must include string keys "explanation" and "challenge_question"'
        )
    explanation = explanation.strip()
    challenge_question = challenge_question.strip()
    if not explanation or not challenge_question:
        raise ExplainerError("Model returned an empty explanation or challenge question")

    return ExplanationResult(
        explanation=explanation, challenge_question=challenge_question
    )
