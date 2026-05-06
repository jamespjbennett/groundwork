import pytest
from knowledge_store import graph_state_from_rows, novelty_cap


def test_novelty_cap_typed():
    assert novelty_cap("typed") == pytest.approx(0.8)


def test_novelty_cap_ai_generated():
    assert novelty_cap("ai_generated") == pytest.approx(0.95)


def test_graph_state_from_rows_empty():
    gs = graph_state_from_rows([])
    assert gs.total_seen == 0
    assert gs.avg_confidence == pytest.approx(0.0)


def test_graph_state_from_rows_builds_correct_records():
    rows = [
        {"id": "decorator", "name": "Decorator", "confidence": 0.6, "seen_count": 2, "last_seen": "2026-01-01"},
        {"id": "lambda", "name": "Lambda", "confidence": 0.3, "seen_count": 1, "last_seen": None},
    ]
    gs = graph_state_from_rows(rows)
    assert gs.total_seen == 2
    ids = {c.id for c in gs.concepts}
    assert ids == {"decorator", "lambda"}
    assert gs.avg_confidence == pytest.approx(0.45)
