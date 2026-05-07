import pytest
from explainer import ExplainerError, ExplanationResult, _parse_model_json, _strip_json_fences


_VALID = (
    '{"summary": "Added a route handler.",'
    ' "explanation": "A decorator wraps a function.",'
    ' "challenge_q": "What does @app.get bind?"}'
)


# --- _strip_json_fences ---

def test_plain_json_is_returned_unchanged():
    assert _strip_json_fences(_VALID) == _VALID.strip()


def test_strips_json_fenced_block():
    raw = f"```json\n{_VALID}\n```"
    assert _strip_json_fences(raw) == _VALID


def test_strips_plain_fenced_block():
    raw = f"```\n{_VALID}\n```"
    assert _strip_json_fences(raw) == _VALID


def test_strips_surrounding_whitespace():
    raw = f"   {_VALID}   "
    assert _strip_json_fences(raw) == _VALID


# --- _parse_model_json: happy path ---

def test_parses_valid_json():
    result = _parse_model_json(_VALID)
    assert isinstance(result, ExplanationResult)
    assert result.summary == "Added a route handler."
    assert result.explanation == "A decorator wraps a function."
    assert result.challenge_question == "What does @app.get bind?"


def test_parses_fenced_json():
    result = _parse_model_json(f"```json\n{_VALID}\n```")
    assert result.summary == "Added a route handler."
    assert result.explanation == "A decorator wraps a function."


def test_recovers_json_fragment_embedded_in_prose():
    text = f"Sure, here it is: {_VALID} Hope that helps."
    result = _parse_model_json(text)
    assert result.summary == "Added a route handler."


# --- key compatibility: challenge_q vs challenge_question ---

def test_accepts_legacy_challenge_question_key():
    text = (
        '{"summary": "s", "explanation": "e",'
        ' "challenge_question": "what?"}'
    )
    assert _parse_model_json(text).challenge_question == "what?"


def test_prefers_challenge_q_when_both_present():
    text = (
        '{"summary": "s", "explanation": "e",'
        ' "challenge_q": "new", "challenge_question": "old"}'
    )
    assert _parse_model_json(text).challenge_question == "new"


# --- _parse_model_json: validation errors ---

def test_raises_when_summary_missing():
    text = '{"explanation": "e", "challenge_q": "q"}'
    with pytest.raises(ExplainerError, match="summary"):
        _parse_model_json(text)


def test_raises_when_explanation_missing():
    text = '{"summary": "s", "challenge_q": "q"}'
    with pytest.raises(ExplainerError, match="explanation"):
        _parse_model_json(text)


def test_raises_when_challenge_missing():
    text = '{"summary": "s", "explanation": "e"}'
    with pytest.raises(ExplainerError, match="challenge_q"):
        _parse_model_json(text)


def test_raises_when_summary_is_empty_string():
    text = '{"summary": "", "explanation": "e", "challenge_q": "q"}'
    with pytest.raises(ExplainerError):
        _parse_model_json(text)


def test_raises_when_explanation_is_empty_string():
    text = '{"summary": "s", "explanation": "", "challenge_q": "q"}'
    with pytest.raises(ExplainerError):
        _parse_model_json(text)


def test_raises_when_challenge_is_empty_string():
    text = '{"summary": "s", "explanation": "e", "challenge_q": ""}'
    with pytest.raises(ExplainerError):
        _parse_model_json(text)


def test_raises_on_non_dict_json():
    with pytest.raises(ExplainerError):
        _parse_model_json('["summary", "explanation"]')


def test_raises_on_completely_invalid_json():
    with pytest.raises(ExplainerError):
        _parse_model_json("not json at all")
