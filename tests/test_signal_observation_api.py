from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def _observations(transaction_id):
    definitions = [
        ("SIG-018", "auth"),
        ("SIG-006", "device"),
        ("SIG-012", "account"),
        ("SIG-004", "beneficiary"),
        ("SIG-002", "velocity"),
    ]
    return [
        {
            "signal_id": signal_id,
            "condition_met": True,
            "evidence_id": f"{transaction_id}-{suffix}",
            "source": "synthetic-api-adapter",
            "observed_at": "2026-11-12T09:00:00Z",
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
            "rule_version": "bank-rule-v1",
            "detector_version": "adapter-v1",
            "scope": "bank_internal",
            "data_mode": "synthetic",
        }
        for signal_id, suffix in definitions
    ]


def test_api_accepts_synthetic_observations_and_keeps_cross_bank_isolated():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-OBS-API-001",
            "bank_id": "bank-a",
            "actor_id": "actor-observation",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "device_id": "synthetic-device",
            "network_id": "synthetic-network",
            "signal_observations": _observations("TX-OBS-API-001"),
            "shadow_mode": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pipeline"]["risk"]["score"] == 80
    assert body["case"] is None
    assert body["citizen_status"]["status"] == "SHADOW_ONLY"
    assert body["audit"][0]["event_type"] == "RISK_EVALUATED_SHADOW"
    assert body["cross_bank"]["matches"] == []


def test_api_rejects_cross_bank_signal_observations():
    observations = _observations("TX-OBS-CROSS")
    observations[0]["scope"] = "cross_bank"
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-OBS-CROSS",
            "bank_id": "bank-a",
            "actor_id": "actor-observation",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_observations": observations,
        },
    )

    assert response.status_code == 400
    assert "cross-bank signal observations are disabled" in response.json()["detail"]


def test_api_rejects_raw_identifiers_in_signal_observations():
    observations = _observations("TX-OBS-RAW")
    observations[0]["card_number"] = "4111111111111111"
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-OBS-RAW",
            "bank_id": "bank-a",
            "actor_id": "actor-observation",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_observations": observations,
        },
    )

    assert response.status_code == 400
    assert "unsupported fields" in response.json()["detail"]


def test_api_rejects_both_raw_signal_events_and_observations():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-OBS-BOTH-API",
            "bank_id": "bank-a",
            "actor_id": "actor-observation",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_events": [],
            "signal_observations": [],
        },
    )

    assert response.status_code == 400
    assert "not both" in response.json()["detail"]
