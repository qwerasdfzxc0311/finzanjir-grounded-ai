from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def test_api_synthetic_decision_does_not_action_case():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-SYNTHETIC-STATUS-001",
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
    body = response.json()
    assert body["decision"]["case"]["status"] == "OPEN"
    assert body["decision"]["audit_event"]["change"]["case_status"] == "OPEN"
