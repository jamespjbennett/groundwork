def calibrate_depth(graph_state: dict) -> str:
    total = graph_state.get("total_seen", 0)
    avg_conf = graph_state.get("avg_confidence", 0.0)

    if total < 10 or avg_conf < 0.3:
        return "beginner"
    if total < 30 or avg_conf < 0.6:
        return "intermediate"
    return "advanced"
