"""Single orchestration path for one analyse pass of the learning loop."""

from typing import Literal

from concept_extractor import extract_concepts
from explainer import explain
from knowledge_store import KnowledgeStore, novelty_cap


async def analyse_submission(
    code: str,
    knowledge: KnowledgeStore,
    origin: Literal["typed", "ai_generated"] = "typed",
) -> dict:
    concepts = extract_concepts(code)
    cap = novelty_cap(origin)
    novel = [
        c for c in concepts if await knowledge.is_novel(c, novel_if_confidence_below=cap)
    ]

    if not novel:
        return {"skipped": True, "reason": "already_known", "concepts": concepts}

    concept = novel[0]
    confidence_before = await knowledge.get_confidence(concept)
    graph_state = await knowledge.get_graph_state()
    result = await explain(concept, code, graph_state)
    await knowledge.upsert(concept, seen=True)

    return {
        "skipped": False,
        "concepts": concepts,
        "novel_concept": concept,
        "explanation": result.explanation,
        "challenge_question": result.challenge_question,
        "confidence_before": confidence_before,
    }
