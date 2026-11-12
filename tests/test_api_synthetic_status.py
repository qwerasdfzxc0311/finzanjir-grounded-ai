from fastapi.testclient import TestClient

from finzanjir_api.app import app
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


client = TestClient(app)


def test_api_synthetic_decision_does_not_action_case():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-API-SYNTHETIC-STATUS-001",
            "bank_id": "bank-a",
            "actor_id": "actor-api-synth-status",
            "amount": 2500,
            "occurred_at": "2026-11-11T00:00:00Z",
            "synthetic": True,
            "signal_events": build_synthetic_case_signal_events(transaction_id="TX-API-SYNTHETIC-STATUS-001", observed_at="2026-11-11T00:00:00Z"),
            "shadow_mode": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["case"]["status"] == "OPEN"
    assert body["decision"]["audit_event"]["change"]["case_status"] == "OPEN"
    assert body["kpi"]["data_mode"] == "synthetic"
    assert body["kpi"]["signal_to_case_rate"] == 0.2
    assert body["kpi"]["case_action_rate"] == 0.0
    assert body["kpi"]["average_review_seconds"] == 0.0
