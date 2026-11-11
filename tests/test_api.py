from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


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


def test_prototype_endpoint_executes_synthetic_flow():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-001",
            "bank_id": "bank-a",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "device_id": "device-1",
            "network_id": "network-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "TX-API-001"
    assert body["pipeline"]["signal"]["transaction_id"] == "TX-API-001"
    assert body["case"]["transaction_id"] == "TX-API-001"
    assert body["cross_bank"]["matches"]
    assert body["decision"]["case"]["case_id"] == body["case"]["case_id"]
    assert len(body["layers_16"]) == 16
