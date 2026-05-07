"""Single orchestration path for one analyse pass of the learning loop.

Pipeline:
  1. Extract concepts from the submitted code via AST.
  2. Decide which are novel (below the confidence cap for this origin).
  3. If none novel → skip; record nothing.
  4. Otherwise: pick the first novel concept as the explanation focus,
     ask the explainer for a contextual {summary, explanation, challenge_q},
     upsert *all* extracted concepts (so reinforced ones bump seen_count),
     and record one entry row linking them with their novelty flags.

The /analyse endpoint always sees a slim response: enough for the
extension to confirm success, with full detail living in the entries
table for the web UI to fetch.
"""

from typing import Literal

from concept_extractor import extract_concepts
from explainer import explain
from knowledge_store import KnowledgeStore, novelty_cap


async def analyse_submission(
    *,
    code: str,
    diff: str,
    file_path: str,
    session_id: str,
    knowledge: KnowledgeStore,
    language: str = "python",
    origin: Literal["typed", "ai_generated"] = "typed",
) -> dict:
    concepts = extract_concepts(code)
    cap = novelty_cap(origin)

    novel_set: set[str] = set()
    for c in concepts:
        if await knowledge.is_novel(c, novel_if_confidence_below=cap):
            novel_set.add(c)

    if not novel_set:
        return {
            "skipped": True,
            "reason": "already_known" if concepts else "no_concepts",
            "concepts": [
                {"id": c, "name": c, "is_novel": False} for c in concepts
            ],
        }

    focus = next(c for c in concepts if c in novel_set)

    graph_state = await knowledge.get_graph_state()
    result = await explain(focus, code, graph_state, file_path=file_path)

    # Upsert every extracted concept — both new and reinforced — so seen_count
    # and last_seen reflect today's activity, then record the entry row.
    for c in concepts:
        await knowledge.upsert(c)

    entry_id = await knowledge.record_entry(
        session_id=session_id,
        file_path=file_path,
        language=language,
        origin=origin,
        diff=diff,
        code_snippet=code,
        summary=result.summary,
        explanation=result.explanation,
        challenge_q=result.challenge_question,
        concepts=[(c, c in novel_set) for c in concepts],
    )

    entry = await knowledge.get_entry(entry_id)
    return {
        "skipped": False,
        "entry_id": entry_id,
        "summary": result.summary,
        "concepts": entry["concepts"] if entry else [],
    }
