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
    summary: str
    explanation: str
    challenge_question: str


async def explain(
    concept_id: str,
    code_snippet: str,
    graph_state: GraphState,
    *,
    file_path: str | None = None,
) -> ExplanationResult:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ExplainerError("ANTHROPIC_API_KEY is not set")

    depth = calibrate_depth(graph_state)
    prompt = _build_prompt(concept_id, code_snippet, file_path, depth)

    text = await _call_model(prompt)
    try:
        return _parse_model_json(text)
    except ExplainerError:
        # One retry with a sharper formatting reminder. Model sometimes wraps
        # the JSON in prose or fences despite instructions.
        retry_prompt = prompt + (
            "\n\nIMPORTANT: Return ONLY a JSON object with exactly these "
            'string keys: "summary", "explanation", "challenge_q". '
            "No prose, no markdown fences, no commentary."
        )
        text = await _call_model(retry_prompt)
        return _parse_model_json(text)


def _build_prompt(
    concept_id: str,
    code_snippet: str,
    file_path: str | None,
    depth: str,
) -> str:
    location = f" in `{file_path}`" if file_path else ""
    return f"""You are a coding tutor reviewing a developer's recent code change.

The developer just wrote code{location} that uses the concept: **{concept_id}**.

The code:
```python
{code_snippet[:2000]}
```

Depth level: {depth}
Style: {_DEPTH_INSTRUCTIONS[depth]}

Return a JSON object with three string keys:

1. "summary" — One sentence describing what THIS specific code change accomplishes. Not what {concept_id} is in general — what THIS code does. Like a commit message: "Added a class to centralise database connection handling".

2. "explanation" — Two to four short paragraphs explaining the {concept_id} concept *as it appears in this code*. Reference actual variable names, function names, and patterns from the snippet above. Explain why {concept_id} was used here and what it achieves in THIS code, not in the abstract.

3. "challenge_q" — One specific question about the code just written. The answer must be verifiable from the snippet. Avoid generic questions like "what is a {concept_id}?".

Return only the JSON object. No commentary, no markdown fences."""


async def _call_model(prompt: str) -> str:
    try:
        message = await _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise ExplainerError(f"Anthropic API error ({type(e).__name__}): {e}") from e
    except httpx.HTTPError as e:
        raise ExplainerError("Could not reach the explanation model (network error)") from e

    return _message_to_text(message)


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

    summary = data.get("summary")
    explanation = data.get("explanation")
    # Prefer the new spec key; fall back to the legacy key if the model returns it.
    challenge = data.get("challenge_q")
    if challenge is None:
        challenge = data.get("challenge_question")

    for name, value in (("summary", summary), ("explanation", explanation), ("challenge_q", challenge)):
        if not isinstance(value, str):
            raise ExplainerError(f"Model JSON must include a string field '{name}'")
        if not value.strip():
            raise ExplainerError(f"Model returned an empty '{name}'")

    return ExplanationResult(
        summary=summary.strip(),
        explanation=explanation.strip(),
        challenge_question=challenge.strip(),
    )
