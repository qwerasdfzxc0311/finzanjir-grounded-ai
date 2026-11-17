from fastapi.testclient import TestClient

from finzanjir_api.app import app
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


client = TestClient(app)


def _multi_signal_fields(transaction_id: str, occurred_at: str) -> dict:
    return {
        "signal_events": build_synthetic_case_signal_events(transaction_id=transaction_id, observed_at=occurred_at),
        "shadow_mode": False,
    }


def test_health_endpoint_reports_runtime_api():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "finzanjir-grounded-ai"


def test_ai_endpoint_answers_from_grounded_knowledge():
    response = client.post(
        "/api/ai/answer",
        json={"question": "FINZANJIR nima?", "runtime_refs": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["generation_mode"] in {
        "model",
        "deterministic_fallback",
        "fallback_refused_long_source",
        "no_grounded_evidence",
        "insufficient_evidence",
        "author_deterministic_fallback",
        "author_insufficient_evidence",
        "general_knowledge_model",
        "general_knowledge_local_facts",
        "general_knowledge_unavailable",
        "general_knowledge_provider_failed",
        "project_overview_localized",
    }
    if body["generation_mode"] in {"model", "deterministic_fallback", "project_overview_localized"}:
        assert body["abstained"] is False
        assert body["knowledge_refs"]
    elif body["generation_mode"] == "fallback_refused_long_source":
        assert body["abstained"] is True
        assert body["knowledge_refs"]
    else:
        assert body["abstained"] is True
        assert body["knowledge_refs"] == []
    assert body["provider_status"] in {
        "ready", "not_configured", "provider_failed", "blocked_sensitive", "not_attempted", "offline_mode"
    }
    assert isinstance(body["provider_diagnostics"], list)
    assert "confidence" in body
    assert "provenance" in body


def test_prototype_endpoint_executes_synthetic_flow_without_cross_bank_authorization():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-001",
            "bank_id": "bank-a",
            "actor_id": "actor-api-001",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-001", "2026-11-11T00:00:00Z"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "TX-API-001"
    assert body["pipeline"]["signal"]["transaction_id"] == "TX-API-001"
    assert body["case"]["transaction_id"] == "TX-API-001"
    assert body["cross_bank"]["matches"] == []
    assert body["decision"]["case"]["case_id"] == body["case"]["case_id"]
    assert len(body["layers_16"]) == 16


def test_prototype_demo_endpoint_returns_a_human_readable_system_explanation():
    response = client.get("/api/prototype/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "synthetic"
    assert body["transaction"]["transaction_id"]
    assert body["flow"]["entry"] == "synthetic_bank"
    assert body["flow"]["final"] == "layers_16"
    assert body["flow"]["stages"]
    assert body["flow"]["stages"][0]["id"] == "synthetic_bank"
    assert body["flow"]["stages"][-1]["id"] == "layers_16"
    assert body["explanation"]["case_is_not_guilt"] is True
    assert body["explanation"]["risk_is_not_guilt"] is True
    assert body["explanation"]["ai_is_not_final_decision_maker"] is True


def test_prototype_endpoint_rejects_coerced_cross_bank_authorization():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-AUTH-TYPE-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
            "cross_bank_authorized": 1,
        },
    )
    assert response.status_code == 422


def test_prototype_endpoint_blocks_unauthorized_cross_bank_exchange():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-CROSS-BANK-UNAUTH-001",
            "bank_id": "bank-a",
            "actor_id": "actor-api-cross-unauth",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
            "cross_bank_authorized": False,
        },
    )

    assert response.status_code == 403
    assert "authorized cross-bank exchange" in response.json()["detail"]


def test_prototype_endpoint_does_not_trust_client_cross_bank_authorization():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-CLIENT-AUTH-001",
            "bank_id": "bank-a",
            "actor_id": "actor-api-client-auth",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
            "cross_bank_authorized": True,
        },
    )

    assert response.status_code == 403
    assert "authorized cross-bank exchange" in response.json()["detail"]


def test_prototype_endpoint_never_returns_authoritative_synthetic_demo_decision():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-SYNTHETIC-AUTH-001",
            "bank_id": "bank-a",
            "actor_id": "actor-api-synth-auth",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-SYNTHETIC-AUTH-001", "2026-11-11T00:00:00Z"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    human_decision = body["decision"]["human_decision"]
    audit_change = body["decision"]["audit_event"]["change"]

    assert human_decision["decision_origin"] == "synthetic_demo"
    assert human_decision["actor_type"] == "synthetic_demo"
    assert human_decision["is_authoritative"] is False
    assert audit_change["decision_origin"] == "synthetic_demo"
    assert audit_change["actor_type"] == "synthetic_demo"
    assert audit_change["is_authoritative"] is False



def test_api_single_amount_context_stays_shadow_only_without_case():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-CONTEXT-ONLY-001",
            "bank_id": "bank-a",
            "actor_id": "actor-context-only",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pipeline"]["risk"]["score"] == 0
    assert body["pipeline"]["risk"]["case_eligible"] is False
    assert body["pipeline"]["signal"]["status"] == "CONTEXT_ONLY"
    assert body["case"] is None
    assert body["decision"] is None
    assert body["citizen_status"]["status"] == "SHADOW_ONLY"
    assert body["audit"][0]["event_type"] == "RISK_EVALUATED_SHADOW"



def test_windows_endpoint_reports_real_layer_implementation_status():
    response = client.get("/api/windows")

    assert response.status_code == 200
    body = response.json()
    assert body["architecture_layers"] == 16
    assert body["layer_status_summary"] == {
        "total": 16,
        "complete": 0,
        "partial": 16,
        "planned": 0,
    }



def test_prototype_demo_exposes_truthful_per_window_execution_trace():
    response = client.get("/api/prototype/demo")
    assert response.status_code == 200
    body = response.json()
    trace = body["window_trace"]

    assert [item["window_id"] for item in trace] == [
        "synthetic_bank",
        "signal_risk",
        "cross_bank_fraud",
        "human_case",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    ]
    assert all(item["transaction_id"] == body["transaction"]["transaction_id"] for item in trace)
    assert all(item["data_mode"] == "synthetic" for item in trace)
    assert next(item for item in trace if item["window_id"] == "cross_bank_fraud")["status"] == "DISABLED"
    assert next(item for item in trace if item["window_id"] == "human_case")["status"] == "SYNTHETIC_REVIEW_ONLY"
    assert next(item for item in trace if item["window_id"] == "layers_16")["status"] == "PARTIAL"


def test_prototype_run_returns_per_window_status_and_reference_trace():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-WINDOW-TRACE",
            "bank_id": "bank-a",
            "actor_id": "actor-api-window-trace",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-WINDOW-TRACE", "2026-11-12T09:00:00Z"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    trace = body["window_trace"]

    assert len(trace) == 8
    assert all(item["transaction_id"] == body["transaction_id"] for item in trace)
    assert next(item for item in trace if item["window_id"] == "cross_bank_fraud")["status"] == "DISABLED"
    assert next(item for item in trace if item["window_id"] == "human_case")["status"] == "SYNTHETIC_REVIEW_ONLY"
    assert next(item for item in trace if item["window_id"] == "layers_16")["status"] == "PARTIAL"



def test_prototype_run_stops_after_signal_module_failure_without_trace_or_history(monkeypatch):
    def fail_signal_module(*args, **kwargs):
        raise ValueError("synthetic signal module failure")

    def history_must_not_be_written():
        raise AssertionError("failed module execution must not be persisted as a completed run")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.process_transaction", fail_signal_module)
    monkeypatch.setattr("finzanjir_api.app.prototype_run_store", history_must_not_be_written)

    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-SIGNAL-FAILURE-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-signal-failure",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "synthetic signal module failure"
    assert "window_trace" not in response.json()
    assert "prototype_run_id" not in response.json()



def test_prototype_run_history_failure_returns_unavailable_without_success_trace(monkeypatch):
    import sqlite3

    class FailingRunStore:
        def save(self, summary):
            raise sqlite3.OperationalError("synthetic storage unavailable")

    monkeypatch.setattr("finzanjir_api.app.prototype_run_store", lambda: FailingRunStore())

    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-HISTORY-FAILURE-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-history-failure",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Prototype run could not be safely saved."
    assert "window_trace" not in response.json()
    assert "prototype_run_id" not in response.json()



def _parse_sse_frames(payload: str) -> list[tuple[str, dict]]:
    import json

    parsed = []
    for frame in payload.strip().split("\n\n"):
        lines = frame.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: ") and lines[1].startswith("data: "):
            parsed.append((lines[0][7:], json.loads(lines[1][6:])))
    return parsed


def test_stream_endpoint_emits_actual_ordered_window_progress_and_final_result(monkeypatch):
    class InMemoryRunStore:
        def save(self, _summary):
            return {"run_id": "run-stream-progress-test"}

    monkeypatch.setattr("finzanjir_api.app.prototype_run_store", lambda: InMemoryRunStore())
    response = client.post(
        "/api/prototype/run/stream",
        json={
            "transaction_id": "TX-API-STREAM-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-stream",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-STREAM-001", "2026-11-12T09:00:00Z"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = _parse_sse_frames(response.text)
    stages = [data for name, data in frames if name == "stage"]
    results = [data for name, data in frames if name == "result"]
    errors = [data for name, data in frames if name == "error"]

    assert len(stages) == 16
    assert [item["window_id"] for item in stages] == [
        window_id
        for window_id in (
            "synthetic_bank", "signal_risk", "cross_bank_fraud", "human_case",
            "audit_kpi", "finzanjir_ai", "citizen", "layers_16",
        )
        for _ in range(2)
    ]
    assert [item["status"] for item in stages[::2]] == ["RUNNING"] * 8
    assert stages[-1]["status"] == "PARTIAL"
    assert len(results) == 1
    assert results[0]["prototype_run_id"] == "run-stream-progress-test"
    assert len(results[0]["window_trace"]) == 8
    assert errors == []


def test_stream_endpoint_reports_failed_and_not_run_stages_without_success_result(monkeypatch):
    def fail_signal_pipeline(*_args, **_kwargs):
        raise ValueError("synthetic signal pipeline failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.process_transaction", fail_signal_pipeline)
    response = client.post(
        "/api/prototype/run/stream",
        json={
            "transaction_id": "TX-API-STREAM-FAIL-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-stream-fail",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-STREAM-FAIL-001", "2026-11-12T09:00:00Z"),
        },
    )

    assert response.status_code == 200
    frames = _parse_sse_frames(response.text)
    stages = [data for name, data in frames if name == "stage"]
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]

    assert [item["status"] for item in stages] == [
        "RUNNING", "COMPLETED", "RUNNING", "FAILED",
        "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN",
        "NOT_RUN", "NOT_RUN",
    ]
    assert stages[3]["window_id"] == "signal_risk"
    assert errors == [{"status_code": 400, "detail": "synthetic signal pipeline failure"}]
    assert results == []



def test_stream_storage_failure_keeps_completed_windows_but_returns_no_success_result(monkeypatch):
    import sqlite3

    class FailingRunStore:
        def save(self, _summary):
            raise sqlite3.OperationalError("synthetic storage unavailable")

    monkeypatch.setattr("finzanjir_api.app.prototype_run_store", lambda: FailingRunStore())
    response = client.post(
        "/api/prototype/run/stream",
        json={
            "transaction_id": "TX-API-STREAM-STORE-FAIL-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-stream-store-fail",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            **_multi_signal_fields("TX-API-STREAM-STORE-FAIL-001", "2026-11-12T09:00:00Z"),
        },
    )

    frames = _parse_sse_frames(response.text)
    stages = [data for name, data in frames if name == "stage"]
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]

    assert len(stages) == 16
    assert all(item["status"] not in {"FAILED", "NOT_RUN"} for item in stages)
    assert errors == [{"status_code": 503, "detail": "Prototype run could not be safely saved."}]
    assert results == []



def test_stream_endpoint_marks_unauthorized_cross_bank_stage_failed_and_stops_later_windows():
    response = client.post(
        "/api/prototype/run/stream",
        json={
            "transaction_id": "TX-API-STREAM-CROSS-FAIL-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-stream-cross-fail",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "device_id": "synthetic-device-1",
            "network_id": "synthetic-network-1",
            "cross_bank_authorized": False,
            **_multi_signal_fields("TX-API-STREAM-CROSS-FAIL-001", "2026-11-12T09:00:00Z"),
        },
    )

    frames = _parse_sse_frames(response.text)
    stages = [data for name, data in frames if name == "stage"]
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]

    assert stages[-6]["window_id"] == "cross_bank_fraud"
    assert stages[-6]["status"] == "FAILED"
    assert [item["status"] for item in stages[-5:]] == ["NOT_RUN"] * 5
    assert errors == [{"status_code": 403, "detail": "authorized cross-bank exchange is required"}]
    assert results == []



def _module_failure_stream_payload(transaction_id: str, *, shadow_mode: bool = False) -> dict:
    return {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-module-failure-matrix",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        **_multi_signal_fields(transaction_id, "2026-11-12T09:00:00Z"),
        "shadow_mode": shadow_mode,
    }


def _stream_events(response):
    frames = _parse_sse_frames(response.text)
    return (
        [data for name, data in frames if name == "stage"],
        [data for name, data in frames if name == "error"],
        [data for name, data in frames if name == "result"],
    )


def test_stream_case_module_failure_stops_before_audit_ai_citizen_and_layers(monkeypatch):
    def fail_case(*_args, **_kwargs):
        raise RuntimeError("synthetic case module failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.CaseManager.apply_human_decision", fail_case)
    response = client.post(
        "/api/prototype/run/stream",
        json=_module_failure_stream_payload("TX-STREAM-CASE-FAIL-001"),
    )
    stages, errors, results = _stream_events(response)

    assert [item["status"] for item in stages] == [
        "RUNNING", "COMPLETED", "RUNNING", "COMPLETED",
        "RUNNING", "DISABLED", "RUNNING", "FAILED",
        "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN",
    ]
    assert stages[7]["window_id"] == "human_case"
    assert errors == [{"status_code": 500, "detail": "Prototype flow failed safely."}]
    assert results == []


def test_stream_ai_module_failure_stops_before_citizen_and_layers(monkeypatch):
    def fail_ai(*_args, **_kwargs):
        raise RuntimeError("synthetic AI module failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.FINZANJIRAI.answer", fail_ai)
    response = client.post(
        "/api/prototype/run/stream",
        json=_module_failure_stream_payload("TX-STREAM-AI-FAIL-001"),
    )
    stages, errors, results = _stream_events(response)

    assert stages[-4]["window_id"] == "finzanjir_ai"
    assert [item["status"] for item in stages[-4:]] == [
        "RUNNING", "FAILED", "NOT_RUN", "NOT_RUN"
    ]
    assert errors == [{"status_code": 500, "detail": "Prototype flow failed safely."}]
    assert results == []


def test_stream_audit_module_failure_stops_shadow_flow_before_ai(monkeypatch):
    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit module failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.AuditLog.append", fail_audit)
    response = client.post(
        "/api/prototype/run/stream",
        json=_module_failure_stream_payload("TX-STREAM-AUDIT-FAIL-001", shadow_mode=True),
    )
    stages, errors, results = _stream_events(response)

    assert stages[-5]["window_id"] == "audit_kpi"
    assert [item["status"] for item in stages[-5:]] == [
        "RUNNING", "FAILED", "NOT_RUN", "NOT_RUN", "NOT_RUN"
    ]
    assert errors == [{"status_code": 500, "detail": "Prototype flow failed safely."}]
    assert results == []


def test_stream_layer_registry_failure_is_reported_without_success_result(monkeypatch):
    def fail_layers(*_args, **_kwargs):
        raise RuntimeError("synthetic layer registry failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.SystemFlow._layer_trace", fail_layers)
    response = client.post(
        "/api/prototype/run/stream",
        json=_module_failure_stream_payload("TX-STREAM-LAYERS-FAIL-001"),
    )
    stages, errors, results = _stream_events(response)

    assert stages[-2]["window_id"] == "layers_16"
    assert [item["status"] for item in stages[-2:]] == ["RUNNING", "FAILED"]
    assert errors == [{"status_code": 500, "detail": "Prototype flow failed safely."}]
    assert results == []



def test_stream_rejects_non_synthetic_input_with_failed_first_stage_and_remaining_not_run():
    response = client.post(
        "/api/prototype/run/stream",
        json={
            "transaction_id": "TX-STREAM-PREFLIGHT-FAIL-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-preflight-fail",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": False,
        },
    )
    stages, errors, results = _stream_events(response)

    assert [item["window_id"] for item in stages] == [
        "synthetic_bank", "signal_risk", "cross_bank_fraud", "human_case",
        "audit_kpi", "finzanjir_ai", "citizen", "layers_16",
    ]
    assert [item["status"] for item in stages] == [
        "FAILED", "NOT_RUN", "NOT_RUN", "NOT_RUN",
        "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN",
    ]
    assert errors == [{
        "status_code": 400,
        "detail": "The prototype flow accepts only explicitly synthetic transactions.",
    }]
    assert results == []



def test_general_knowledge_api_returns_local_fact_and_source_provenance():
    response = client.post(
        "/api/ai/answer",
        json={"question": "Nega osmon ko‘k?", "runtime_refs": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_mode"] == "general_knowledge_local_facts"
    assert body["provider_status"] == "not_attempted"
    assert body["abstained"] is False
    assert "Rayleigh" in body["answer"]
    assert "https://www.weather.gov/fgz/SkyBlue" in body["provenance"]
    assert "https://spaceplace.nasa.gov/blue-sky/en/" in body["provenance"]
