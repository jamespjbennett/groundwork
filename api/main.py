from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

from concept_extractor import extract_concepts
from knowledge_graph import KnowledgeGraph
from explainer import explain

app = FastAPI(title="Groundwork API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = KnowledgeGraph()


class AnalyseRequest(BaseModel):
    code: str
    language: str = "python"
    origin: Literal["typed", "ai_generated"] = "typed"


class RespondRequest(BaseModel):
    concept_id: str
    understood: bool


@app.on_event("startup")
async def startup():
    await db.init()


@app.post("/analyse")
async def analyse(req: AnalyseRequest):
    concepts = extract_concepts(req.code)
    novel = [c for c in concepts if await db.is_novel(c)]

    if not novel:
        return {"skipped": True, "reason": "already_known", "concepts": concepts}

    concept = novel[0]
    result = await explain(concept, req.code, await db.get_graph_state())
    await db.upsert(concept, seen=True)

    return {
        "skipped": False,
        "concepts": concepts,
        "novel_concept": concept,
        "explanation": result["explanation"],
        "challenge_question": result["challenge_question"],
        "confidence_before": await db.get_confidence(concept),
    }


@app.post("/respond")
async def respond(req: RespondRequest):
    updated = await db.update(req.concept_id, req.understood)
    return {"updated_concept": updated}


@app.get("/concepts")
async def concepts():
    return {"concepts": await db.all()}


@app.get("/session/digest")
async def digest():
    return await db.session_digest()
