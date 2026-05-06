import pytest
from depth_calibrator import calibrate_depth
from graph_state import ConceptRecord, GraphState

_TS = "2026-01-01T00:00:00+00:00"


def make_graph(n: int, confidence: float) -> GraphState:
    records = tuple(
        ConceptRecord(id=str(i), name=str(i), confidence=confidence, seen_count=1, last_seen=_TS)
        for i in range(n)
    )
    return GraphState(records)


def test_empty_graph_is_beginner():
    assert calibrate_depth(GraphState(())) == "beginner"


def test_few_concepts_below_threshold_is_beginner():
    assert calibrate_depth(make_graph(5, 0.8)) == "beginner"


def test_low_avg_confidence_is_beginner_regardless_of_count():
    assert calibrate_depth(make_graph(20, 0.2)) == "beginner"


def test_boundary_at_10_concepts_with_sufficient_confidence_is_intermediate():
    # Use 0.35 — 0.3 accumulated over 10 floats sits just below 0.3 due to fp precision
    # total=10 is not < 10; avg=0.35 is not < 0.3 → passes beginner gate
    # total=10 is < 30 → intermediate
    assert calibrate_depth(make_graph(10, 0.35)) == "intermediate"


def test_mid_range_is_intermediate():
    assert calibrate_depth(make_graph(20, 0.5)) == "intermediate"


def test_high_count_but_low_confidence_stays_intermediate():
    # total=35 >= 30, but avg=0.5 < 0.6 → second branch fires → intermediate
    assert calibrate_depth(make_graph(35, 0.5)) == "intermediate"


def test_boundary_at_30_concepts_and_0_6_confidence_is_advanced():
    # total=30 is not < 30; avg=0.6 is not < 0.6 → advanced
    assert calibrate_depth(make_graph(30, 0.6)) == "advanced"


def test_clearly_advanced():
    assert calibrate_depth(make_graph(50, 0.9)) == "advanced"
