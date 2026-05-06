from graph_state import GraphState


def calibrate_depth(state: GraphState) -> str:
    total = state.total_seen
    avg_conf = state.avg_confidence

    if total < 10 or avg_conf < 0.3:
        return "beginner"
    if total < 30 or avg_conf < 0.6:
        return "intermediate"
    return "advanced"
