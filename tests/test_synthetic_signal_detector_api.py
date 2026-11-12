from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def test_detector_catalogue_exposes_40_synthetic_only_rules():
    response = client.get("/api/prototype/detectors")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 40
    assert body["data_mode"] == "synthetic"
    assert body["cross_bank_data_enabled"] is False
    assert all(item["status"] == "synthetic_test_only" for item in body["detectors"])


def test_prototype_run_can_detect_and_score_multiple_synthetic_features():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-DETECTOR-INTEGRATION-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "synthetic-actor",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "shadow_mode": False,
            "detector_scenario_id": "five-family-positive",
            "signal_features": {
                "mfa_strength_decreased": True,
                "mfa_change_to_transfer_seconds": 300,
                "device_age_hours": 1,
                "trusted_device": False,
                "password_reset_to_transfer_seconds": 300,
                "beneficiary_age_days": 1,
                "beneficiary_prior_transaction_count": 0,
                "transaction_count_10m": 5,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detector"]["detected_count"] == 5
    assert body["pipeline"]["risk"]["score"] == 80
    assert body["pipeline"]["risk"]["independent_families"] == 5
    assert body["pipeline"]["risk"]["case_eligible"] is True
    assert body["case"]["data_mode"] == "synthetic"
    assert body["case"]["transaction_id"] == "TX-DETECTOR-INTEGRATION-001"
    assert body["decision"] is not None
    assert body["bank_status"] is not None
    assert body["citizen_status"] is not None
    assert body["audit"]
    assert body["ai"] is not None
    assert body["kpi"]["data_mode"] == "synthetic"
    assert len(body["layers_16"]) == 16
    assert body["cross_bank"]["matches"] == []


def test_detector_api_rejects_unapproved_identity_features():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-DETECTOR-PII-001",
            "bank_id": "bank-a",
            "amount": 100,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_features": {"account_number": "123456789"},
        },
    )
    assert response.status_code == 400
    assert "unsupported feature fields" in response.json()["detail"]


def test_detector_api_rejects_mixed_precomputed_and_feature_inputs():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-DETECTOR-MIXED-001",
            "bank_id": "bank-a",
            "amount": 100,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_features": {"app_language_changed": True},
            "signal_events": [],
        },
    )
    assert response.status_code == 400
    assert "not both" in response.json()["detail"]


def test_detector_api_does_not_accept_non_synthetic_data():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-DETECTOR-REAL-001",
            "bank_id": "bank-a",
            "amount": 100,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": False,
            "signal_features": {"app_language_changed": True},
        },
    )
    assert response.status_code == 400


def test_detector_features_flow_through_shadow_without_case_or_bank_action():
    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-DETECTOR-SHADOW-001",
            "bank_id": "bank-synthetic-a",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "shadow_mode": True,
            "detector_scenario_id": "five-family-shadow",
            "signal_features": {
                "mfa_strength_decreased": True,
                "mfa_change_to_transfer_seconds": 300,
                "device_age_hours": 1,
                "trusted_device": False,
                "password_reset_to_transfer_seconds": 300,
                "beneficiary_age_days": 1,
                "beneficiary_prior_transaction_count": 0,
                "transaction_count_10m": 5,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detector"]["detected_count"] == 5
    assert body["pipeline"]["risk"]["score"] == 80
    assert body["pipeline"]["risk"]["case_eligible"] is True
    assert body["case"] is None
    assert body["decision"] is None
    assert body["bank_status"] is None
    assert body["citizen_status"]["status"] == "SHADOW_ONLY"
    assert body["citizen_status"]["case_id"] is None
    assert body["kpi"]["cases_opened"] == 0
    assert len(body["audit"]) == 1
    assert body["cross_bank"]["matches"] == []
    assert len(body["layers_16"]) == 16
