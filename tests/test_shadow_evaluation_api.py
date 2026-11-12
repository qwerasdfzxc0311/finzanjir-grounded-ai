from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def test_shadow_evaluation_api_accepts_only_explicit_synthetic_scenarios():
    response = client.post(
        "/api/prototype/shadow-evaluate",
        json={
            "scenarios": [
                {"scenario_id": "benign-1", "expected_label": "benign", "synthetic": True, "signal_events": []},
                {"scenario_id": "suspicious-1", "expected_label": "suspicious", "synthetic": True, "signal_events": [
                    {"signal_id": "SIG-018", "evidence_id": "auth", "source": "synthetic", "observed_at": "2026-11-12T09:00:00Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                    {"signal_id": "SIG-006", "evidence_id": "device", "source": "synthetic", "observed_at": "2026-11-12T09:00:01Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                    {"signal_id": "SIG-012", "evidence_id": "account", "source": "synthetic", "observed_at": "2026-11-12T09:00:02Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                    {"signal_id": "SIG-004", "evidence_id": "beneficiary", "source": "synthetic", "observed_at": "2026-11-12T09:00:03Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                    {"signal_id": "SIG-002", "evidence_id": "velocity", "source": "synthetic", "observed_at": "2026-11-12T09:00:04Z", "evidence_quality": 1.0, "recency_factor": 1.0},
                ]},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "synthetic"
    assert body["scenario_count"] == 2
    assert body["confusion_matrix"] == {"tp": 1, "fp": 0, "tn": 1, "fn": 0}


def test_shadow_evaluation_api_rejects_non_synthetic_scenarios():
    response = client.post(
        "/api/prototype/shadow-evaluate",
        json={
            "scenarios": [
                {"scenario_id": "real-1", "expected_label": "benign", "synthetic": False, "signal_events": []}
            ]
        },
    )

    assert response.status_code == 400
