from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, StrictBool
from starlette.staticfiles import StaticFiles

from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.shadow import evaluate_shadow_batch
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


class AIAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    runtime_refs: list[str] = Field(default_factory=list, max_length=64)
    working_memory_scope: str | None = Field(default=None, max_length=256)


class ShadowScenario(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=128)
    expected_label: Literal["suspicious", "benign"]
    synthetic: StrictBool
    signal_events: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class ShadowEvaluationRequest(BaseModel):
    scenarios: list[ShadowScenario] = Field(min_length=1, max_length=500)
    escalation_threshold: float = Field(default=75, ge=0, le=100)


class PrototypeTransaction(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    bank_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(default="", max_length=128)
    amount: float = Field(ge=0)
    occurred_at: str = Field(min_length=1, max_length=64)
    synthetic: StrictBool = False
    device_id: str = Field(default="", max_length=128)
    network_id: str = Field(default="", max_length=128)
    cross_bank_authorized: StrictBool = False
    signal_events: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    signal_observations: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    shadow_mode: StrictBool = True


def _parse_allowed_origins(raw: str | None) -> list[str]:
    """Parse an explicit browser-origin allowlist; an unset value is same-origin only."""
    if not raw:
        return []
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if "*" in origins:
        raise RuntimeError("FINZANJIR_ALLOWED_ORIGINS must not contain wildcard origins")
    if any(not (origin.startswith("https://") or origin.startswith("http://")) for origin in origins):
        raise RuntimeError("FINZANJIR_ALLOWED_ORIGINS entries must be absolute HTTP(S) origins")
    if len(origins) != len(set(origins)):
        raise RuntimeError("FINZANJIR_ALLOWED_ORIGINS entries must be unique")
    return origins


_ALLOWED_ORIGINS = _parse_allowed_origins(os.getenv("FINZANJIR_ALLOWED_ORIGINS"))


app = FastAPI(
    title="FINZANJIR Grounded AI API",
    version="0.1.0",
    description="Shared runtime API for the connected FINZANJIR prototype.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


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
        "layer_status_summary": flow.layer_status_summary(),
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


@app.post("/api/prototype/shadow-evaluate")
def shadow_evaluate(request: ShadowEvaluationRequest) -> dict[str, Any]:
    if any(scenario.synthetic is not True for scenario in request.scenarios):
        raise HTTPException(
            status_code=400,
            detail="Shadow evaluation accepts only explicitly synthetic scenarios.",
        )
    scenarios = [scenario.model_dump(exclude={"synthetic"}) for scenario in request.scenarios]
    return evaluate_shadow_batch(
        scenarios,
        escalation_threshold=request.escalation_threshold,
    )


@app.get("/api/prototype/demo")
def prototype_demo() -> dict[str, Any]:
    """Execute a deterministic synthetic scenario for the prototype presentation."""
    transaction = {
        "transaction_id": "TX-DEMO-2500",
        "bank_id": "bank-a",
        "actor_id": "actor-demo-2500",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id="TX-DEMO-2500",
            observed_at="2026-11-11T00:00:00Z",
        ),
        "shadow_mode": False,
        # Public presentation demo is fail-closed: it contains no cross-bank
        # identifiers and carries no client/server authorization claim.
        "cross_bank_authorized": False,
    }
    flow = build_system_flow()
    result = flow.execute(transaction, knowledge_index=knowledge_index())
    explanation = flow.explain_result(result)
    response = {
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
    response["runtime"]["cross_bank_authorized"] = transaction["cross_bank_authorized"]
    return response


@app.post("/api/prototype/run")
def run_prototype(transaction: PrototypeTransaction) -> dict[str, Any]:
    if transaction.synthetic is not True:
        raise HTTPException(
            status_code=400,
            detail="The prototype flow accepts only explicitly synthetic transactions.",
        )

    flow = build_system_flow()
    try:
        payload = transaction.model_dump()
        # Authorization is a trusted server-side decision, never a client claim.
        # The public prototype endpoint therefore fails closed for cross-bank access.
        payload["cross_bank_authorized"] = False
        result = flow.execute(
            payload,
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
