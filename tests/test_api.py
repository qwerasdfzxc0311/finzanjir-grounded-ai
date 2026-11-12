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
    assert body["abstained"] is False
    assert body["answer"]
    assert body["knowledge_refs"]
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
        "partial": 12,
        "planned": 4,
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
