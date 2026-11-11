from fastapi.testclient import TestClient

import finzanjir_api.app as api_module
from finzanjir_api.app import app
from finzanjir_ai.knowledge.index import build_knowledge_index


client = TestClient(app)


def test_health_contract_is_live_and_presentation_safe():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "finzanjir-grounded-ai",
    }


def test_prototype_demo_executes_connected_runtime_flow():
    response = client.get("/api/prototype/demo")

    assert response.status_code == 200
    body = response.json()

    assert body["data_mode"] == "synthetic"
    assert body["runtime"]["transaction_id"] == "TX-DEMO-2500"
    assert body["runtime"]["case_opened"] is True
    assert body["runtime"]["cross_bank_matches"] >= 1
    assert body["runtime"]["layers_covered"] == 16
    assert body["explanation"]["synthetic_data_only"] is True


def test_prototype_run_rejects_non_synthetic_data_at_api_boundary():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-REAL-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": False,
        },
    )

    assert response.status_code == 400
    assert "only explicitly synthetic" in response.json()["detail"]


def test_prototype_run_accepts_explicit_synthetic_transaction_without_cross_bank_access():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-SYNTH-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "TX-SYNTH-001"
    assert body["pipeline"]["signal"]["transaction_id"] == "TX-SYNTH-001"


def test_prototype_run_requires_explicit_cross_bank_authorization():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-CROSSBANK-UNAUTH-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
        },
    )

    assert response.status_code == 403
    assert "authorized cross-bank exchange" in response.json()["detail"]


def test_prototype_run_allows_cross_bank_matching_only_when_authorized():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-CROSSBANK-AUTH-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
            "cross_bank_authorized": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["cross_bank"]["matches"]


def test_prototype_run_rejects_requests_that_omit_the_synthetic_boundary_flag():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-AMBIGUOUS-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
        },
    )

    assert response.status_code == 400
    assert "only explicitly synthetic" in response.json()["detail"]


def test_ai_api_abstains_when_runtime_knowledge_is_empty(monkeypatch):
    monkeypatch.setattr(api_module, "knowledge_index", lambda: build_knowledge_index([]))

    response = client.post(
        "/api/ai/answer",
        json={"question": "Unsupported fact with no grounded evidence"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["confidence"] < 0.35
