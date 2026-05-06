import pytest
from graph_state import ConceptRecord, GraphState

_TS = "2026-01-01T00:00:00+00:00"


def rec(id: str, confidence: float) -> ConceptRecord:
    return ConceptRecord(id=id, name=id, confidence=confidence, seen_count=1, last_seen=_TS)


# --- GraphState ---

def test_empty_graph_total_seen():
    assert GraphState(()).total_seen == 0


def test_empty_graph_avg_confidence():
    assert GraphState(()).avg_confidence == 0.0


def test_total_seen_counts_records():
    gs = GraphState((rec("a", 0.5), rec("b", 0.7)))
    assert gs.total_seen == 2


def test_avg_confidence_is_mean():
    gs = GraphState((rec("a", 0.4), rec("b", 0.6)))
    assert gs.avg_confidence == pytest.approx(0.5)


def test_avg_confidence_single_record():
    gs = GraphState((rec("x", 0.75),))
    assert gs.avg_confidence == pytest.approx(0.75)


# --- ConceptRecord.from_store ---

def test_from_store_round_trip():
    row = {
        "id": "decorator",
        "name": "Decorator",
        "confidence": 0.75,
        "seen_count": 3,
        "last_seen": _TS,
    }
    r = ConceptRecord.from_store(row)
    assert r.id == "decorator"
    assert r.name == "Decorator"
    assert r.confidence == pytest.approx(0.75)
    assert r.seen_count == 3
    assert r.last_seen == _TS


def test_from_store_confidence_coerced_to_float():
    row = {"id": "x", "name": "x", "confidence": "0.5", "seen_count": 1, "last_seen": None}
    r = ConceptRecord.from_store(row)
    assert isinstance(r.confidence, float)


def test_from_store_seen_count_coerced_to_int():
    row = {"id": "x", "name": "x", "confidence": 0.5, "seen_count": "2", "last_seen": None}
    r = ConceptRecord.from_store(row)
    assert isinstance(r.seen_count, int)
    assert r.seen_count == 2
