import pytest

from finzanjir_ai.risk.observations import normalize_signal_observations
from finzanjir_ai.risk.registry import SIGNAL_REGISTRY


def _observation(signal_id, evidence_id, **overrides):
    item = {
        "signal_id": signal_id,
        "condition_met": True,
        "evidence_id": evidence_id,
        "source": "synthetic-bank-adapter",
        "observed_at": "2026-11-12T09:00:00Z",
        "evidence_quality": 1.0,
        "recency_factor": 1.0,
        "rule_version": "rule-v1",
        "detector_version": "detector-v1",
        "scope": "bank_internal",
        "data_mode": "synthetic",
    }
    item.update(overrides)
    return item


def test_adapter_normalizes_all_40_registry_signal_observations():
    observations = [
        _observation(signal_id, f"evidence-{signal_id}")
        for signal_id in SIGNAL_REGISTRY
    ]

    events = normalize_signal_observations(observations)

    assert len(events) == 40
    assert {event["signal_id"] for event in events} == set(SIGNAL_REGISTRY)
    assert all(event["rule_version"] == "rule-v1" for event in events)
    assert all(event["detector_version"] == "detector-v1" for event in events)


def test_adapter_ignores_unmatched_conditions_without_creating_signal_events():
    events = normalize_signal_observations([
        _observation("SIG-001", "not-matched", condition_met=False)
    ])
    assert events == []


def test_adapter_rejects_cross_bank_and_real_data():
    with pytest.raises(ValueError, match="cross-bank"):
        normalize_signal_observations([_observation("SIG-001", "ev-cross", scope="cross_bank")])
    with pytest.raises(ValueError, match="synthetic data only"):
        normalize_signal_observations([_observation("SIG-001", "ev-real")], data_mode="real")


def test_adapter_rejects_raw_identifiers_and_unknown_fields():
    with pytest.raises(ValueError, match="unsupported fields"):
        normalize_signal_observations([
            _observation("SIG-001", "ev-raw", card_number="4111111111111111")
        ])


def test_adapter_rejects_unknown_signal_and_invalid_detector_provenance():
    with pytest.raises(ValueError, match="unknown signal_id"):
        normalize_signal_observations([_observation("SIG-999", "ev-unknown")])
    with pytest.raises(ValueError, match="rule_version"):
        normalize_signal_observations([_observation("SIG-001", "ev-no-rule", rule_version="")])
    with pytest.raises(ValueError, match="evidence_quality"):
        normalize_signal_observations([_observation("SIG-001", "ev-quality", evidence_quality=1.5)])


def test_adapter_rejects_more_than_100_observations():
    observations = [
        _observation("SIG-001", f"ev-{index}")
        for index in range(101)
    ]
    with pytest.raises(ValueError, match="100 items"):
        normalize_signal_observations(observations)
