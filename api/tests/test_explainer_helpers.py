import pytest
from explainer import ExplainerError, ExplanationResult, _parse_model_json, _strip_json_fences


# --- _strip_json_fences ---

def test_plain_json_is_returned_unchanged():
    raw = '{"explanation": "A decorator wraps a function.", "challenge_question": "What?"}'
    assert _strip_json_fences(raw) == raw.strip()


def test_strips_json_fenced_block():
    raw = '```json\n{"explanation": "e", "challenge_question": "q"}\n```'
    result = _strip_json_fences(raw)
    assert result == '{"explanation": "e", "challenge_question": "q"}'


def test_strips_plain_fenced_block():
    raw = '```\n{"explanation": "e", "challenge_question": "q"}\n```'
    result = _strip_json_fences(raw)
    assert result == '{"explanation": "e", "challenge_question": "q"}'


def test_strips_surrounding_whitespace():
    raw = '   {"explanation": "e", "challenge_question": "q"}   '
    result = _strip_json_fences(raw)
    assert result == '{"explanation": "e", "challenge_question": "q"}'


# --- _parse_model_json ---

def test_parses_valid_json():
    text = '{"explanation": "A decorator wraps a function.", "challenge_question": "What does @property do?"}'
    result = _parse_model_json(text)
    assert isinstance(result, ExplanationResult)
    assert result.explanation == "A decorator wraps a function."
    assert result.challenge_question == "What does @property do?"


def test_parses_fenced_json():
    text = '```json\n{"explanation": "e", "challenge_question": "q"}\n```'
    result = _parse_model_json(text)
    assert result.explanation == "e"
    assert result.challenge_question == "q"


def test_raises_when_explanation_key_missing():
    with pytest.raises(ExplainerError):
        _parse_model_json('{"challenge_question": "q"}')


def test_raises_when_challenge_question_key_missing():
    with pytest.raises(ExplainerError):
        _parse_model_json('{"explanation": "e"}')


def test_raises_when_explanation_is_empty_string():
    with pytest.raises(ExplainerError):
        _parse_model_json('{"explanation": "", "challenge_question": "q"}')


def test_raises_when_challenge_question_is_empty_string():
    with pytest.raises(ExplainerError):
        _parse_model_json('{"explanation": "e", "challenge_question": ""}')


def test_raises_on_non_dict_json():
    with pytest.raises(ExplainerError):
        _parse_model_json('["explanation", "challenge_question"]')


def test_raises_on_completely_invalid_json():
    with pytest.raises(ExplainerError):
        _parse_model_json("not json at all")


def test_recovers_json_fragment_embedded_in_prose():
    # Model sometimes wraps JSON in a sentence before/after.
    text = 'Sure, here it is: {"explanation": "e", "challenge_question": "q"} Hope that helps.'
    result = _parse_model_json(text)
    assert result.explanation == "e"
    assert result.challenge_question == "q"
