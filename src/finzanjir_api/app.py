from __future__ import annotations

import asyncio
import json
import httpx
from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, StrictBool
from starlette.staticfiles import StaticFiles

from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.orchestration.engine import FINZANJIRAI, get_finzanjir_ai
from finzanjir_ai.orchestration.intent import classify_query_intent
from finzanjir_ai.research.tavily import TavilySearchClient
from finzanjir_ai.integrations.cloud_sources import cloud_connector_status
from finzanjir_ai.integrations.google_cloud import router as google_cloud_router
from finzanjir_ai.risk.shadow import evaluate_shadow_batch, evaluate_detector_shadow_batch
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events
from finzanjir_ai.risk.detectors import synthetic_signal_detector
from finzanjir_ai.storage.prototype_history import PrototypeRunStore, default_database_path
import sqlite3


class AIConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class AIAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    runtime_refs: list[str] = Field(default_factory=list, max_length=64)
    working_memory_scope: str | None = Field(default=None, max_length=256)
    conversation_history: list[AIConversationTurn] = Field(default_factory=list, max_length=12)


class ExternalResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=8)


class ShadowScenario(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=128)
    expected_label: Literal["suspicious", "benign"]
    synthetic: StrictBool
    signal_events: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class ShadowEvaluationRequest(BaseModel):
    scenarios: list[ShadowScenario] = Field(min_length=1, max_length=500)
    escalation_threshold: float = Field(default=75, ge=0, le=100)


class DetectorShadowScenario(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=128)
    expected_label: Literal["suspicious", "benign"]
    synthetic: StrictBool
    observed_at: str = Field(min_length=1, max_length=64)
    target_signal_ids: list[str] = Field(min_length=1, max_length=40)
    features: dict[str, Any] = Field(default_factory=dict, max_length=100)
    evidence_quality: float = Field(default=1.0, ge=0, le=1)
    recency_factor: float = Field(default=1.0, ge=0, le=1)


class DetectorShadowEvaluationRequest(BaseModel):
    scenarios: list[DetectorShadowScenario] = Field(min_length=1, max_length=500)
    escalation_threshold: float = Field(default=75, ge=0, le=100)


class PrototypeTransaction(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    bank_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(default="synthetic-demo-actor", max_length=128)
    amount: float = Field(ge=0)
    occurred_at: str = Field(min_length=1, max_length=64)
    synthetic: StrictBool = False
    device_id: str = Field(default="", max_length=128)
    network_id: str = Field(default="", max_length=128)
    cross_bank_authorized: StrictBool = False
    signal_events: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    signal_observations: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    shadow_mode: StrictBool = True
    signal_features: dict[str, Any] | None = None
    detector_scenario_id: str = Field(default="synthetic-prototype", min_length=1, max_length=128)
    detector_evidence_quality: float = Field(default=1.0, ge=0, le=1)
    detector_recency_factor: float = Field(default=1.0, ge=0, le=1)


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

app.include_router(google_cloud_router)


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
def prototype_run_store() -> PrototypeRunStore:
    return PrototypeRunStore(default_database_path())


@lru_cache(maxsize=1)
def knowledge_index() -> KnowledgeIndex:
    return build_system_flow().demo_knowledge_index()


@lru_cache(maxsize=1)
def ai_engine() -> FINZANJIRAI:
    # Retrieval statistics are precomputed once for the canonical corpus.
    return FINZANJIRAI(knowledge_index())


@app.get("/api/cloud/connectors")
def cloud_connectors() -> dict[str, Any]:
    """Expose safe connector readiness only; never expose credentials or files."""
    configured = {
        name for name in (
            "FINZANJIR_DROPBOX_CLIENT_ID",
            "FINZANJIR_MICROSOFT_CLIENT_ID",
            "FINZANJIR_GOOGLE_CLIENT_ID",
        ) if os.getenv(name)
    }
    return cloud_connector_status(configured)


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

    if classify_query_intent(question) == "web_search":
        try:
            research = TavilySearchClient().search(question, max_results=5)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Internet qidiruvi hozir sozlanmagan yoki vaqtincha mavjud emas.") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Internet qidiruv xizmati vaqtincha javob bermadi.") from exc
        sources = research.get("results", [])
        summary = (
            "Internet qidiruvi natijalari. Quyidagi sahifalar tashqi manbalardir; ular FINZANJIRning tasdiqlangan loyiha hujjatlari hisoblanmaydi."
            if sources else "Internet qidiruvi bajarildi, ammo mos natijalar topilmadi."
        )
        return {
            "answer": summary,
            "confidence": 0.0,
            "abstained": not bool(sources),
            "generation_mode": "web_search",
            "provider_status": "not_attempted",
            "provider_diagnostics": [],
            "knowledge_refs": [],
            "provenance": [],
            "runtime_refs": list(request.runtime_refs),
            "external_sources": sources,
        }

    scope = request.working_memory_scope or (request.runtime_refs[0] if request.runtime_refs else "conversation")
    engine = get_finzanjir_ai(knowledge_index())
    result = engine.answer(
        question,
        runtime_refs=tuple(request.runtime_refs),
        working_memory_scope=scope,
        conversation_history=tuple(turn.model_dump() for turn in request.conversation_history),
    )

    return {
        "answer": result.answer.answer,
        "confidence": result.answer.confidence,
        "abstained": result.answer.abstained,
        "generation_mode": result.answer.generation_mode,
        "provider_status": result.answer.provider_status,
        "provider_diagnostics": list(getattr(engine.language_model, "last_provider_failures", ())),
        "knowledge_refs": list(result.answer.citations),
        "provenance": [
            str(source)
            for item in result.grounded_context.items
            for source in item.provenance
        ],
        "runtime_refs": list(result.runtime_context.runtime_refs),
        "external_sources": [],
    }


@app.post("/api/research/search")
def external_research(request: ExternalResearchRequest) -> dict[str, Any]:
    try:
        return TavilySearchClient().search(request.query, max_results=request.max_results)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="External research is not configured.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="External research provider is temporarily unavailable.") from exc


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


@app.post("/api/prototype/detector-shadow-evaluate")
def detector_shadow_evaluate(request: DetectorShadowEvaluationRequest) -> dict[str, Any]:
    if any(scenario.synthetic is not True for scenario in request.scenarios):
        raise HTTPException(
            status_code=400,
            detail="Detector shadow evaluation accepts only explicitly synthetic scenarios.",
        )
    scenarios = [scenario.model_dump() for scenario in request.scenarios]
    return evaluate_detector_shadow_batch(
        scenarios,
        escalation_threshold=request.escalation_threshold,
    )


@app.get("/api/prototype/detectors")
def prototype_detectors() -> dict[str, Any]:
    detector = synthetic_signal_detector()
    return {
        "data_mode": "synthetic",
        "scope": "bank_internal",
        "status": "synthetic_test_only",
        "cross_bank_data_enabled": False,
        "count": len(detector.catalogue()),
        "detectors": detector.catalogue(),
    }


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
        "window_trace": flow.build_window_trace(result),
        "explanation": explanation["explanation"],
    }
    response["runtime"]["cross_bank_authorized"] = transaction["cross_bank_authorized"]
    return response


def _execute_prototype(
    transaction: PrototypeTransaction,
    *,
    on_stage: Any = None,
) -> dict[str, Any]:
    if transaction.synthetic is not True:
        raise HTTPException(
            status_code=400,
            detail="The prototype flow accepts only explicitly synthetic transactions.",
        )

    flow = build_system_flow()
    try:
        payload = transaction.model_dump()
        detector_result = None
        if payload.get("signal_features") is not None:
            if payload.get("signal_events") is not None or payload.get("signal_observations") is not None:
                raise ValueError("provide signal_features or precomputed signal events/observations, not both")
            detector_result = synthetic_signal_detector().evaluate(
                scenario_id=payload["detector_scenario_id"],
                observed_at=payload["occurred_at"],
                features=payload["signal_features"],
                evidence_quality=payload["detector_evidence_quality"],
                recency_factor=payload["detector_recency_factor"],
            )
            payload["signal_observations"] = detector_result["signal_observations"]
        payload.pop("signal_features", None)
        payload.pop("detector_scenario_id", None)
        payload.pop("detector_evidence_quality", None)
        payload.pop("detector_recency_factor", None)
        # Authorization is a trusted server-side decision, never a client claim.
        # The public prototype endpoint therefore fails closed for cross-bank access.
        payload["cross_bank_authorized"] = False
        result = flow.execute(
            payload,
            knowledge_index=knowledge_index(),
            on_stage=on_stage,
        )
    except ValueError as exc:
        if "authorized cross-bank exchange" in str(exc):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pipeline = result["pipeline"]
    risk = pipeline.risk or {}
    summary = {
        "data_mode": "synthetic",
        "risk_score": risk.get("score", 0),
        "risk_level": risk.get("level", "OBSERVE"),
        "threshold": risk.get("escalation_threshold", (risk.get("threshold") or {}).get("value", 75) if isinstance(risk.get("threshold"), dict) else risk.get("threshold", 75)),
        "signal_count": len(pipeline.signals),
        "evidence_count": risk.get("evidence_count", len(pipeline.evidences)),
        "independent_families": risk.get("independent_families", 0),
        "case_eligible": bool(risk.get("case_eligible", False)),
        "case_opened": result.get("case") is not None,
        "shadow_mode": bool(risk.get("shadow_mode", True)),
        "engine_version": risk.get("engine_version", "unknown"),
        "registry_version": risk.get("registry_version", "unknown"),
    }
    try:
        saved_run = prototype_run_store().save(summary)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Prototype run could not be safely saved.") from exc
    response = jsonable_encoder(result)
    response["window_trace"] = flow.build_window_trace(result)
    # Expose only the minimal synthetic transaction summary needed by the UI.
    # Do not echo actor, device, network, raw features or evidence identifiers.
    response["transaction"] = {
        "transaction_id": payload["transaction_id"],
        "bank_id": payload["bank_id"],
        "amount": payload["amount"],
        "occurred_at": payload["occurred_at"],
        "synthetic": True,
    }
    response["prototype_run_id"] = saved_run["run_id"]
    if detector_result is not None:
        response["detector"] = detector_result
    return response


@app.post("/api/prototype/run")
def run_prototype(transaction: PrototypeTransaction) -> dict[str, Any]:
    return _execute_prototype(transaction)


@app.post("/api/prototype/run/stream")
async def stream_prototype(transaction: PrototypeTransaction) -> StreamingResponse:
    """Stream actual backend window-stage events; no client-side simulated progress."""
    async def event_stream():
        queue: asyncio.Queue[tuple[str, dict[str, Any] | None]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        flow = build_system_flow()
        state: dict[str, Any] = {
            "active": None,
            "last_event": None,
            "transaction_id": transaction.transaction_id,
        }

        def publish(event_name: str, data: dict[str, Any] | None) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, (event_name, data))
            except RuntimeError:
                # A disconnected client must not interrupt the synthetic core flow.
                return

        def on_stage(event: dict[str, Any]) -> None:
            state["last_event"] = event
            if event.get("status") == "RUNNING":
                state["active"] = event
            elif state["active"] and state["active"].get("window_id") == event.get("window_id"):
                state["active"] = None
            publish("stage", event)

        def worker() -> None:
            try:
                result = _execute_prototype(transaction, on_stage=on_stage)
            except HTTPException as exc:
                active = state.get("active")
                last_event = state.get("last_event")
                failed_sequence = None
                if active:
                    failed_sequence = active["sequence"]
                elif last_event and last_event.get("sequence", 0) < len(flow.window_ids):
                    failed_sequence = last_event["sequence"] + 1
                elif not last_event:
                    # HTTP preflight rejection occurs before the first stage event.
                    failed_sequence = 1
                if failed_sequence is not None:
                    failed_window = flow.window_ids[failed_sequence - 1]
                    publish("stage", {
                        "sequence": failed_sequence,
                        "window_id": failed_window,
                        "transaction_id": transaction.transaction_id,
                        "data_mode": "synthetic",
                        "status": "FAILED",
                        "summary": "Bosqich xato sabab xavfsiz to‘xtadi.",
                        "input_refs": [],
                        "output_refs": [],
                    })
                    for sequence, window_id in enumerate(flow.window_ids[failed_sequence:], start=failed_sequence + 1):
                        publish("stage", {
                            "sequence": sequence,
                            "window_id": window_id,
                            "transaction_id": transaction.transaction_id,
                            "data_mode": "synthetic",
                            "status": "NOT_RUN",
                            "summary": "Oldingi bosqich to‘xtagani sabab bajarilmadi.",
                            "input_refs": [],
                            "output_refs": [],
                        })
                publish("error", {"status_code": exc.status_code, "detail": exc.detail})
            except Exception:
                active = state.get("active")
                last_event = state.get("last_event")
                failed_sequence = None
                if active:
                    failed_sequence = active["sequence"]
                elif last_event and last_event.get("sequence", 0) < len(flow.window_ids):
                    failed_sequence = last_event["sequence"] + 1
                elif not last_event:
                    # Preflight failures (for example, non-synthetic input) happen
                    # before the first stage emits RUNNING; expose that stop honestly.
                    failed_sequence = 1
                if failed_sequence is not None:
                    failed_window = flow.window_ids[failed_sequence - 1]
                    failed_payload = active if active and active.get("sequence") == failed_sequence else {
                        "sequence": failed_sequence,
                        "window_id": failed_window,
                        "transaction_id": transaction.transaction_id,
                        "data_mode": "synthetic",
                        "input_refs": [],
                        "output_refs": [],
                    }
                    publish("stage", {
                        **failed_payload,
                        "status": "FAILED",
                        "summary": "Ichki modul yoki dastlabki tekshiruv xatosi sabab bosqich xavfsiz to‘xtadi.",
                    })
                    for sequence, window_id in enumerate(flow.window_ids[failed_sequence:], start=failed_sequence + 1):
                        publish("stage", {
                            "sequence": sequence,
                            "window_id": window_id,
                            "transaction_id": transaction.transaction_id,
                            "data_mode": "synthetic",
                            "status": "NOT_RUN",
                            "summary": "Oldingi bosqich to‘xtagani sabab bajarilmadi.",
                            "input_refs": [],
                            "output_refs": [],
                        })
                publish("error", {"status_code": 500, "detail": "Prototype flow failed safely."})
            else:
                publish("result", result)
            finally:
                publish("end", None)

        task = asyncio.create_task(asyncio.to_thread(worker))
        while True:
            event_name, data = await queue.get()
            if event_name == "end":
                break
            yield f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        await task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/prototype/runs")
def prototype_runs(limit: int = Query(default=50, ge=1, le=100)) -> dict[str, Any]:
    try:
        runs = prototype_run_store().list_recent(limit=limit)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Prototype run history is temporarily unavailable.") from exc
    return {
        "data_mode": "synthetic",
        "retention_days": prototype_run_store().retention_days,
        "count": len(runs),
        "runs": runs,
        "privacy_note": "Only aggregate synthetic run metrics are stored; transaction, citizen, account, device and raw evidence identifiers are not stored in run history.",
        "persistence_note": "SQLite history is stored on the service filesystem and may be lost after restart or redeploy on an ephemeral host unless a persistent disk is configured.",
    }


frontend_dir= Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
