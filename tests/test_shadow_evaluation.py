import pytest

from finzanjir_ai.risk.shadow import evaluate_shadow_batch


def _high_risk_events(prefix):
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
            "evidence_id": f"{prefix}-{evidence_suffix}",
            "source": "synthetic-shadow-test",
            "observed_at": "2026-11-12T09:00:00Z",
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
        }
        for signal_id, evidence_suffix in definitions
    ]


def test_shadow_batch_reports_confusion_matrix_and_metrics_for_synthetic_labels():
    scenarios = [
        {"scenario_id": f"tp-{index}", "expected_label": "suspicious", "signal_events": _high_risk_events(f"tp-{index}")}
        for index in range(4)
    ]
    scenarios.extend([
        {"scenario_id": f"tn-{index}", "expected_label": "benign", "signal_events": []}
        for index in range(3)
    ])
    scenarios.append({
        "scenario_id": "fp-1",
        "expected_label": "benign",
        "signal_events": _high_risk_events("fp-1"),
    })
    scenarios.append({
        "scenario_id": "fn-1",
        "expected_label": "suspicious",
        "signal_events": [{
            "signal_id": "SIG-001",
            "evidence_id": "fn-amount",
            "source": "synthetic-shadow-test",
            "observed_at": "2026-11-12T09:00:00Z",
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
        }],
    })

    result = evaluate_shadow_batch(scenarios)

    assert result["data_mode"] == "synthetic"
    assert result["scenario_count"] == 9
    assert result["confusion_matrix"] == {"tp": 4, "fp": 1, "tn": 3, "fn": 1}
    assert result["metrics"]["precision"] == 0.8
    assert result["metrics"]["recall"] == 0.8
    assert result["metrics"]["specificity"] == 0.75
    assert result["metrics"]["false_positive_rate"] == 0.25
    assert result["metrics"]["false_negative_rate"] == 0.2
    assert result["metrics"]["accuracy"] == 0.7778
    assert result["metrics"]["referral_rate"] == 0.5556
    assert all("case" not in item for item in result["results"])
    assert any("does not measure raw-data detector recall" in item for item in result["limitations"])


def test_shadow_batch_empty_dataset_returns_zero_metrics():
    result = evaluate_shadow_batch([])

    assert result["scenario_count"] == 0
    assert result["metrics"]["precision"] == 0
    assert result["metrics"]["recall"] == 0
    assert result["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}


def test_shadow_batch_rejects_duplicate_scenario_ids():
    scenario = {"scenario_id": "duplicate", "expected_label": "benign", "signal_events": []}
    with pytest.raises(ValueError, match="duplicate scenario_id"):
        evaluate_shadow_batch([scenario, scenario])


def test_shadow_batch_rejects_unknown_expected_label():
    with pytest.raises(ValueError, match="expected_label"):
        evaluate_shadow_batch([{
            "scenario_id": "bad-label",
            "expected_label": "unknown",
            "signal_events": [],
        }])


def test_shadow_batch_rejects_more_than_500_scenarios():
    scenarios = [
        {"scenario_id": f"scenario-{index}", "expected_label": "benign", "signal_events": []}
        for index in range(501)
    ]
    with pytest.raises(ValueError, match="500 items"):
        evaluate_shadow_batch(scenarios)


def _detector_high_features():
    return {
        "mfa_strength_decreased": True,
        "mfa_change_to_transfer_seconds": 300,
        "device_age_hours": 1,
        "trusted_device": False,
        "password_reset_to_transfer_seconds": 300,
        "beneficiary_age_days": 1,
        "beneficiary_prior_transaction_count": 0,
        "transaction_count_10m": 5,
    }


def _detector_scenario(scenario_id, expected_label, target_signal_ids, features):
    return {
        "scenario_id": scenario_id,
        "expected_label": expected_label,
        "synthetic": True,
        "observed_at": "2026-11-12T09:00:00Z",
        "target_signal_ids": target_signal_ids,
        "features": features,
        "evidence_quality": 1.0,
        "recency_factor": 1.0,
    }


def test_detector_shadow_evaluates_source_features_and_reports_decisive_metrics():
    from finzanjir_ai.risk.shadow import evaluate_detector_shadow_batch

    high_ids = ["SIG-018", "SIG-006", "SIG-012", "SIG-004", "SIG-002"]
    high = _detector_high_features()
    benign = {
        "amount_to_customer_p95_ratio": 1.2,
        "customer_baseline_sample_count": 20,
    }
    scenarios = [
        _detector_scenario(f"detector-tp-{i}", "suspicious", high_ids, high)
        for i in range(4)
    ]
    scenarios.extend([
        _detector_scenario(f"detector-tn-{i}", "benign", ["SIG-001"], benign)
        for i in range(3)
    ])
    scenarios.append(_detector_scenario("detector-fp", "benign", high_ids, high))
    scenarios.append(_detector_scenario("detector-fn", "suspicious", ["SIG-001"], benign))

    result = evaluate_detector_shadow_batch(scenarios)

    assert result["evaluation_mode"] == "detector_and_scoring_shadow_metrics_only"
    assert result["confusion_matrix"] == {"tp": 4, "fp": 1, "tn": 3, "fn": 1}
    assert result["coverage"] == 1.0
    assert result["abstention_rate"] == 0.0
    assert result["metrics"]["precision"] == 0.8
    assert result["metrics"]["recall"] == 0.8
    assert result["results"][0]["detected_signal_ids"] == ["SIG-002", "SIG-004", "SIG-006", "SIG-012", "SIG-018"]
    assert result["results"][0]["score"] == 80
    assert result["results"][0]["case_eligible"] is True


def test_detector_shadow_missing_target_features_are_abstentions_not_benign():
    from finzanjir_ai.risk.shadow import evaluate_detector_shadow_batch

    result = evaluate_detector_shadow_batch([
        _detector_scenario("missing-target", "suspicious", ["SIG-001"], {}),
    ])

    assert result["abstained_count"] == 1
    assert result["coverage"] == 0
    assert result["abstention_rate"] == 1
    assert result["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    assert result["results"][0]["predicted_label"] == "abstained_insufficient_data"


def test_detector_shadow_rejects_raw_identity_features():
    from finzanjir_ai.risk.shadow import evaluate_detector_shadow_batch

    with pytest.raises(ValueError, match="unsupported feature fields"):
        evaluate_detector_shadow_batch([
            _detector_scenario("pii-feature", "benign", ["SIG-001"], {"account_number": "123"}),
        ])
