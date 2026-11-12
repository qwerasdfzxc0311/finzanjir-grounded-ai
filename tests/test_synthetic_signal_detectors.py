import json
from pathlib import Path

import pytest

from finzanjir_ai.risk.detectors import SyntheticSignalDetector
from finzanjir_ai.risk.registry import SIGNAL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts" / "signal_detector_rules_v1.json").read_text(encoding="utf-8"))


def _fixture(rule):
    values = {}
    for condition in rule["all_of"]:
        field, op, expected = condition["field"], condition["op"], condition["value"]
        if op in {"eq", "gte", "lte"}:
            values[field] = expected
        elif op == "gt":
            values[field] = expected + 1
        elif op == "lt":
            values[field] = expected - 1
        elif op == "ne":
            values[field] = "__different__" if isinstance(expected, str) else not expected
        elif op == "in":
            values[field] = expected[0]
    return values


def _negative_fixture(rule):
    values = _fixture(rule)
    condition = rule["all_of"][0]
    field, op, expected = condition["field"], condition["op"], condition["value"]
    if op == "eq":
        values[field] = "__not_equal__" if isinstance(expected, str) else not expected
    elif op in {"gte", "gt"}:
        values[field] = expected - 1
    elif op in {"lte", "lt"}:
        values[field] = expected + 1
    elif op == "in":
        values[field] = "__not_in_set__"
    elif op == "ne":
        values[field] = expected
    return values


def test_detector_rule_contract_covers_registry_without_cross_bank_data():
    detector = SyntheticSignalDetector()
    assert CONTRACT["rule_count"] == 40
    assert {item["signal_id"] for item in CONTRACT["detectors"]} == set(SIGNAL_REGISTRY)
    assert len(detector.catalogue()) == 40
    assert all(item["cross_bank_data_enabled"] is False for item in detector.catalogue())
    assert all(item["status"] == "synthetic_test_only" for item in detector.catalogue())


@pytest.mark.parametrize("rule", CONTRACT["detectors"], ids=lambda item: item["signal_id"])
def test_every_signal_detector_has_a_positive_synthetic_feature_path(rule):
    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"positive-{rule['signal_id']}",
        observed_at="2026-11-12T09:00:00Z",
        features=_fixture(rule),
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "DETECTED"
    assert result["data_mode"] == "synthetic"
    assert all(item["data_mode"] == "synthetic" for item in result["signal_observations"])


@pytest.mark.parametrize("rule", CONTRACT["detectors"], ids=lambda item: item["signal_id"])
def test_every_signal_detector_has_a_negative_synthetic_feature_path(rule):
    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"negative-{rule['signal_id']}",
        observed_at="2026-11-12T09:00:00Z",
        features=_negative_fixture(rule),
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "NOT_DETECTED"


@pytest.mark.parametrize(
    "rule",
    [item for item in CONTRACT["detectors"] if item["benign_if"]],
    ids=lambda item: item["signal_id"],
)
def test_benign_counter_evidence_suppresses_candidate_detection(rule):
    features = _fixture(rule)
    benign = rule["benign_if"][0]
    features[benign["field"]] = benign["value"]
    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"benign-{rule['signal_id']}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "SUPPRESSED_BENIGN"
    assert outcome["reason_code"] == "benign_counter_evidence"


def test_missing_features_are_not_misclassified_as_negative_or_suspicious():
    result = SyntheticSignalDetector().evaluate(
        scenario_id="missing-fields",
        observed_at="2026-11-12T09:00:00Z",
        features={},
    )
    assert result["detected_count"] == 0
    assert all(item["status"] == "INSUFFICIENT_DATA" for item in result["detections"])


def test_detector_rejects_identity_and_unapproved_fields():
    detector = SyntheticSignalDetector()
    with pytest.raises(ValueError, match="unsupported feature fields"):
        detector.evaluate(
            scenario_id="no-pii",
            observed_at="2026-11-12T09:00:00Z",
            features={"account_number": "123456789", "customer_name": "Example"},
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"observed_at": "2026-11-12T09:00:00"},
        {"evidence_quality": float("nan")},
        {"recency_factor": 1.1},
        {"scenario_id": ""},
    ],
)
def test_detector_rejects_invalid_timestamp_or_evidence_metadata(kwargs):
    arguments = {
        "scenario_id": "invalid-metadata",
        "observed_at": "2026-11-12T09:00:00Z",
        "features": {},
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        SyntheticSignalDetector().evaluate(**arguments)


def test_detected_signal_observations_are_unique_and_have_provenance():
    rule = next(item for item in CONTRACT["detectors"] if item["signal_id"] == "SIG-036")
    features = _fixture(rule)
    result = SyntheticSignalDetector().evaluate(
        scenario_id="micro-test",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    observation = result["signal_observations"][0]
    assert observation["signal_id"] == "SIG-036"
    assert observation["evidence_id"] == "micro-test:SIG-036"
    assert observation["scope"] == "bank_internal"
    assert observation["rule_version"] == "1.0.0-candidate"
    assert observation["corroborating_signal_ids"] == []
