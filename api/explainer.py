import os
import anthropic
from depth_calibrator import calibrate_depth

_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_DEPTH_INSTRUCTIONS = {
    "beginner": "Explain simply, avoid jargon, use an everyday analogy.",
    "intermediate": "Be concise. Assume basic Python knowledge. Skip trivial definitions.",
    "advanced": "Be precise and brief. Mention edge cases or internals if relevant.",
}


async def explain(concept_id: str, code_snippet: str, graph_state: dict) -> dict:
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

    message = await _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text = message.content[0].text.strip()
    # strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
