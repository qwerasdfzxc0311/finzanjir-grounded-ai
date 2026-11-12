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


def test_detector_shadow_api_runs_feature_detection_and_scoring():
    high_features = {
        "mfa_strength_decreased": True,
        "mfa_change_to_transfer_seconds": 300,
        "device_age_hours": 1,
        "trusted_device": False,
        "password_reset_to_transfer_seconds": 300,
        "beneficiary_age_days": 1,
        "beneficiary_prior_transaction_count": 0,
        "transaction_count_10m": 5,
    }
    response = client.post(
        "/api/prototype/detector-shadow-evaluate",
        json={
            "scenarios": [{
                "scenario_id": "api-detector-high",
                "expected_label": "suspicious",
                "synthetic": True,
                "observed_at": "2026-11-12T09:00:00Z",
                "target_signal_ids": ["SIG-018", "SIG-006", "SIG-012", "SIG-004", "SIG-002"],
                "features": high_features,
            }],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "synthetic"
    assert body["results"][0]["detected_signal_ids"] == ["SIG-002", "SIG-004", "SIG-006", "SIG-012", "SIG-018"]
    assert body["results"][0]["score"] == 80
    assert body["results"][0]["case_eligible"] is True


def test_detector_shadow_api_rejects_non_synthetic_scenarios():
    response = client.post(
        "/api/prototype/detector-shadow-evaluate",
        json={
            "scenarios": [{
                "scenario_id": "real-input",
                "expected_label": "benign",
                "synthetic": False,
                "observed_at": "2026-11-12T09:00:00Z",
                "target_signal_ids": ["SIG-001"],
                "features": {"amount_to_customer_p95_ratio": 1, "customer_baseline_sample_count": 20},
            }],
        },
    )
    assert response.status_code == 400


def test_detector_shadow_api_reports_missing_target_as_abstention():
    response = client.post(
        "/api/prototype/detector-shadow-evaluate",
        json={
            "scenarios": [{
                "scenario_id": "missing-input",
                "expected_label": "suspicious",
                "synthetic": True,
                "observed_at": "2026-11-12T09:00:00Z",
                "target_signal_ids": ["SIG-001"],
                "features": {},
            }],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["abstained_count"] == 1
    assert body["coverage"] == 0
    assert body["results"][0]["predicted_label"] == "abstained_insufficient_data"
