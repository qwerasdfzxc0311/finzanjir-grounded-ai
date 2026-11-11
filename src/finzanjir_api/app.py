from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.orchestration.engine import FINZANJIRAI


class AIAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    runtime_refs: list[str] = Field(default_factory=list, max_length=64)
    working_memory_scope: str | None = Field(default=None, max_length=256)


class PrototypeTransaction(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    bank_id: str = Field(min_length=1, max_length=128)
    amount: float = Field(ge=0)
    occurred_at: str = Field(min_length=1, max_length=64)
    synthetic: bool = False
    device_id: str = Field(default="", max_length=128)
    network_id: str = Field(default="", max_length=128)
    cross_bank_authorized: bool = False


app = FastAPI(
    title="FINZANJIR Grounded AI API",
    version="0.1.0",
    description="Shared runtime API for the connected FINZANJIR prototype.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def knowledge_index() -> KnowledgeIndex:
    return build_system_flow().demo_knowledge_index()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "finzanjir-grounded-ai"}


@app.get("/api/windows")
def windows() -> dict[str, Any]:
    flow = build_system_flow()
    return {
        "entry": flow.window_ids[0],
        "final": flow.window_ids[-1],
        "window_ids": list(flow.window_ids),
        "transitions": [list(item) for item in flow.transitions],
        "architecture_layers": flow.architecture_layers,
        "data_mode": "synthetic",
    }


@app.post("/api/ai/answer")
def answer(request: AIAnswerRequest) -> dict[str, Any]:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty")

    scope = request.working_memory_scope or (request.runtime_refs[0] if request.runtime_refs else "conversation")
    result = FINZANJIRAI(knowledge_index()).answer(
        question,
        runtime_refs=tuple(request.runtime_refs),
        working_memory_scope=scope,
    )

    return {
        "answer": result.answer.answer,
        "confidence": result.answer.confidence,
        "abstained": result.answer.abstained,
        "knowledge_refs": list(result.answer.citations),
        "provenance": [
            str(source)
            for item in result.grounded_context.items
            for source in item.provenance
        ],
        "runtime_refs": list(result.runtime_context.runtime_refs),
    }


@app.get("/api/prototype/demo")
def prototype_demo() -> dict[str, Any]:
    """Execute a deterministic synthetic scenario for the prototype presentation."""
    transaction = {
        "transaction_id": "TX-DEMO-2500",
        "bank_id": "bank-a",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "device_id": "device-demo",
        "network_id": "network-demo",
    }
    flow = build_system_flow()
    result = flow.execute(transaction, knowledge_index=knowledge_index())
    explanation = flow.explain_result(result)
    return {
        "data_mode": "synthetic",
        "transaction": transaction,
        "flow": {
            "entry": flow.window_ids[0],
            "final": flow.window_ids[-1],
            "stages": explanation["stages"],
        },
        "runtime": explanation["runtime"],
        "explanation": explanation["explanation"],
    }


@app.post("/api/prototype/run")
def run_prototype(transaction: PrototypeTransaction) -> dict[str, Any]:
    if transaction.synthetic is not True:
        raise HTTPException(
            status_code=400,
            detail="The prototype flow accepts only explicitly synthetic transactions.",
        )

    flow = build_system_flow()
    try:
        result = flow.execute(
            transaction.model_dump(),
            knowledge_index=knowledge_index(),
        )
    except ValueError as exc:
        if "authorized cross-bank exchange" in str(exc):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return jsonable_encoder(result)


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
