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
