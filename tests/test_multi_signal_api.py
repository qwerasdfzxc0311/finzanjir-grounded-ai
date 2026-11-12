from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def test_prototype_api_exposes_multi_signal_result_in_shadow_mode():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-MULTI-SHADOW-001",
            "bank_id": "bank-a",
            "actor_id": "actor-multi-001",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "device_id": "synthetic-device-shadow",
            "network_id": "synthetic-network-shadow",
            "signal_events": [
                {"signal_id": "SIG-018", "evidence_id": "ev-auth", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:00Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                {"signal_id": "SIG-006", "evidence_id": "ev-device", "source": "synthetic-device", "observed_at": "2026-11-12T08:59:10Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                {"signal_id": "SIG-012", "evidence_id": "ev-account", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:20Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                {"signal_id": "SIG-004", "evidence_id": "ev-beneficiary", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:30Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                {"signal_id": "SIG-002", "evidence_id": "ev-velocity", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:40Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pipeline"]["risk"]["score"] == 80
    assert body["pipeline"]["risk"]["case_eligible"] is True
    assert body["pipeline"]["risk"]["shadow_mode"] is True
    assert body["case"] is None
    assert body["citizen_status"]["status"] == "SHADOW_ONLY"
    assert body["citizen_status"]["risk_score"] == 80
    assert body["citizen_status"]["case_eligible"] is True
    assert body["audit"][0]["event_type"] == "RISK_EVALUATED_SHADOW"
    assert body["audit"][0]["details"]["no_bank_action"] is True
    assert body["pipeline"]["risk"]["id"] in body["ai"]["runtime_context"]["runtime_refs"]
