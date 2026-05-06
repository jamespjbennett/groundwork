from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

from analyse_workflow import analyse_submission
from explainer import ExplainerError
from knowledge_graph import KnowledgeGraph

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
    try:
        return await analyse_submission(req.code, db, req.origin)
    except ExplainerError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


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
