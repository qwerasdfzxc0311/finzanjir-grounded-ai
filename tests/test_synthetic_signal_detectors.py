import json
from pathlib import Path

import pytest

from finzanjir_ai.risk.detectors import SyntheticSignalDetector, _matches
from finzanjir_ai.risk.registry import SIGNAL_REGISTRY
from finzanjir_ai.risk.pipeline import process_transaction


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
    for condition in rule["all_of"]:
        field, op, expected = condition["field"], condition["op"], condition["value"]
        if op == "eq":
            candidate = "__not_equal__" if isinstance(expected, str) else not expected
        elif op == "gte":
            candidate = expected - 1
        elif op == "gt":
            candidate = expected
        elif op == "lte":
            candidate = expected + 1
        elif op == "lt":
            candidate = expected
        elif op == "in":
            candidate = "__not_in_set__"
        elif op == "ne":
            candidate = expected
        else:
            continue

        # A negative fixture must violate one detector condition without
        # introducing an invalid value for another declared non-negative field.
        violates_domain = any(
            guard["field"] == field
            and guard["op"] == "gte"
            and guard["value"] == 0
            and (not isinstance(candidate, (int, float)) or isinstance(candidate, bool) or candidate < 0)
            for guard in rule["all_of"]
        )
        if not violates_domain:
            values[field] = candidate
            return values

    raise AssertionError(f"No valid negative fixture could be built for {rule['signal_id']}")


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
    assert observation["event_key"] == "micro-test:SIG-036"
    assert observation["scope"] == "bank_internal"
    assert observation["rule_version"] == "1.0.0-candidate"
    assert observation["corroborating_signal_ids"] == []


def test_optional_provenance_features_are_allowed_but_not_required():
    rule = next(item for item in CONTRACT["detectors"] if item["signal_id"] == "SIG-013")
    features = _fixture(rule)
    features["watchlist_list_version"] = "watchlist-v3"
    result = SyntheticSignalDetector().evaluate(
        scenario_id="optional-provenance",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == "SIG-013")
    assert outcome["status"] == "DETECTED"
    assert outcome["observed_optional_features"] == ["watchlist_list_version"]


@pytest.mark.parametrize(
    "rule,missing_field",
    [
        (rule, field)
        for rule in CONTRACT["detectors"]
        for field in rule["required_features"]
    ],
    ids=[f"{rule['signal_id']}-{field}" for rule in CONTRACT["detectors"] for field in rule["required_features"]],
)
def test_each_signal_abstains_when_any_required_feature_is_missing(rule, missing_field):
    features = _fixture(rule)
    features.pop(missing_field)
    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"missing-{rule['signal_id']}-{missing_field}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "INSUFFICIENT_DATA"
    assert missing_field in outcome["missing_features"]


@pytest.mark.parametrize(
    "rule,condition",
    [
        (rule, condition)
        for rule in CONTRACT["detectors"]
        for condition in rule["all_of"]
    ],
    ids=[f"{rule['signal_id']}-{condition['field']}" for rule in CONTRACT["detectors"] for condition in rule["all_of"]],
)
def test_each_signal_threshold_boundary_is_inclusive_or_exact_as_declared(rule, condition):
    features = _fixture(rule)
    field, op, threshold = condition["field"], condition["op"], condition["value"]
    if op == "in":
        features[field] = threshold[0]
    else:
        features[field] = threshold

    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"boundary-{rule['signal_id']}-{field}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "DETECTED", (rule["signal_id"], condition, outcome)



@pytest.mark.parametrize(
    "rule,condition",
    [
        (rule, condition)
        for rule in CONTRACT["detectors"]
        for condition in rule["all_of"]
        if condition["op"] == "gte" and condition["value"] == 0
    ],
    ids=[
        f"{rule['signal_id']}-{condition['field']}"
        for rule in CONTRACT["detectors"]
        for condition in rule["all_of"]
        if condition["op"] == "gte" and condition["value"] == 0
    ],
)
def test_negative_nonnegative_feature_values_abstain_instead_of_being_called_benign(rule, condition):
    features = _fixture(rule)
    field = condition["field"]
    features[field] = -1

    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"negative-domain-{rule['signal_id']}-{field}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])

    assert outcome["status"] == "INSUFFICIENT_DATA"
    assert outcome["reason_code"] == "invalid_feature_values"
    assert outcome["invalid_features"] == [field]
    assert outcome["missing_features"] == []



@pytest.mark.parametrize(
    "signal_id,field,bad_value",
    [
        ("SIG-006", "device_age_hours", "1"),
        ("SIG-006", "trusted_device", "false"),
    ],
)
def test_detector_type_mismatch_abstains_instead_of_being_called_benign(signal_id, field, bad_value):
    rule = next(item for item in CONTRACT["detectors"] if item["signal_id"] == signal_id)
    features = _fixture(rule)
    features[field] = bad_value

    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"type-mismatch-{signal_id}-{field}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == signal_id)

    assert outcome["status"] == "INSUFFICIENT_DATA"
    assert outcome["reason_code"] == "invalid_feature_values"
    assert outcome["invalid_features"] == [field]


def test_ne_operator_does_not_treat_type_mismatch_as_inequality():
    condition = {"op": "ne", "value": False}

    assert _matches("false", condition) is False
    assert _matches(False, condition) is False
    assert _matches(True, condition) is True



def _type_mismatch_value(condition):
    operator, expected = condition["op"], condition["value"]
    if operator in {"gt", "gte", "lt", "lte"}:
        return "not-a-number"
    if operator in {"eq", "ne"}:
        if isinstance(expected, bool):
            return "not-a-boolean"
        if isinstance(expected, str):
            return 123
        return "not-a-number"
    if operator == "in":
        first = expected[0]
        if isinstance(first, bool):
            return "not-a-boolean"
        if isinstance(first, str):
            return 123
        return "not-a-number"
    raise AssertionError(f"Unsupported test operator: {operator}")


@pytest.mark.parametrize(
    "rule,field",
    [
        (rule, field)
        for rule in CONTRACT["detectors"]
        for field in sorted({condition["field"] for condition in rule["all_of"]})
    ],
    ids=[
        f"{rule['signal_id']}-{field}"
        for rule in CONTRACT["detectors"]
        for field in sorted({condition["field"] for condition in rule["all_of"]})
    ],
)
def test_every_detector_required_feature_type_mismatch_abstains(rule, field):
    features = _fixture(rule)
    condition = next(item for item in rule["all_of"] if item["field"] == field)
    features[field] = _type_mismatch_value(condition)

    result = SyntheticSignalDetector().evaluate(
        scenario_id=f"type-mismatch-{rule['signal_id']}-{field}",
        observed_at="2026-11-12T09:00:00Z",
        features=features,
    )
    outcome = next(item for item in result["detections"] if item["signal_id"] == rule["signal_id"])

    assert outcome["status"] == "INSUFFICIENT_DATA"
    assert outcome["reason_code"] == "invalid_feature_values"
    assert field in outcome["invalid_features"]



@pytest.mark.parametrize("rule", CONTRACT["detectors"], ids=lambda item: item["signal_id"])
def test_every_signal_zero_recency_factor_contributes_zero_priority(rule):
    detection = SyntheticSignalDetector().evaluate(
        scenario_id=f"zero-recency-{rule['signal_id']}",
        observed_at="2026-11-12T09:00:00Z",
        features=_fixture(rule),
        recency_factor=0,
    )
    outcome = next(item for item in detection["detections"] if item["signal_id"] == rule["signal_id"])
    assert outcome["status"] == "DETECTED"
    assert detection["signal_observations"]
    assert all(item["recency_factor"] == 0 for item in detection["signal_observations"])

    pipeline = process_transaction(
        {
            "transaction_id": f"TX-ZERO-RECENCY-{rule['signal_id']}",
            "bank_id": "bank-synthetic",
            "actor_id": "actor-synthetic",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_observations": detection["signal_observations"],
            "shadow_mode": True,
        },
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert pipeline.risk["score"] == 0
    assert pipeline.risk["case_eligible"] is False
    assert pipeline.case is None
