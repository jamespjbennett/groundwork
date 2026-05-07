from datetime import date as date_cls
from typing import Literal

from dotenv import load_dotenv

load_dotenv()  # must run before explainer.py initialises its anthropic client

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    diff: str
    file_path: str
    session_id: str
    language: str = "python"
    origin: Literal["typed", "ai_generated"] = "typed"


class RespondBody(BaseModel):
    understood: bool


@app.on_event("startup")
async def startup():
    await db.init()


# ---- write ----

@app.post("/analyse")
async def analyse(req: AnalyseRequest):
    try:
        return await analyse_submission(
            code=req.code,
            diff=req.diff,
            file_path=req.file_path,
            session_id=req.session_id,
            knowledge=db,
            language=req.language,
            origin=req.origin,
        )
    except ExplainerError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/concepts/{concept_id}/respond")
async def respond_concept(concept_id: str, body: RespondBody):
    updated = await db.update(concept_id, body.understood)
    if not updated:
        raise HTTPException(status_code=404, detail="concept not found")
    return {
        "confidence": updated["confidence"],
        "depth_level": updated["depth_level"],
    }


# ---- read ----

@app.get("/feed")
async def feed(
    session_id: str | None = None,
    concept_id: str | None = None,
    limit: int = 50,
):
    return {
        "entries": await db.get_feed(
            session_id=session_id, concept_id=concept_id, limit=limit
        )
    }


@app.get("/feed/{entry_id}")
async def feed_entry(entry_id: str):
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="entry not found")
    return entry


@app.get("/digest")
async def digest(date: date_cls | None = None):
    return await db.get_digest(date.isoformat() if date else None)


@app.get("/concepts")
async def concepts():
    return {"concepts": await db.all()}
