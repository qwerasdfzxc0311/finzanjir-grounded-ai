import pytest

from finzanjir_ai.risk.observations import assess_observation_quality, normalize_signal_observations
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


def test_adapter_preserves_explicit_source_event_key_and_defaults_to_evidence_id():
    events = normalize_signal_observations([
        _observation("SIG-006", "ev-device", event_key="source-device-event-7"),
        _observation("SIG-035", "ev-app",),
    ])
    assert events[0]["event_key"] == "source-device-event-7"
    assert events[1]["event_key"] == "ev-app"


def test_adapter_rejects_empty_source_event_key():
    with pytest.raises(ValueError, match="event_key"):
        normalize_signal_observations([
            _observation("SIG-006", "ev-device", event_key=" "),
        ])


def test_adapter_rejects_non_opaque_source_event_keys():
    with pytest.raises(ValueError, match="event_key"):
        normalize_signal_observations([
            _observation("SIG-006", "ev-device", event_key="customer name"),
        ])


def test_quality_monitor_accepts_fresh_ordered_synthetic_observations_without_changing_score():
    observations = normalize_signal_observations([
        _observation("SIG-001", "ev-1", event_key="event-1", observed_at="2026-11-13T09:00:00Z"),
        _observation("SIG-006", "ev-2", event_key="event-2", observed_at="2026-11-13T09:10:00Z"),
    ])

    report = assess_observation_quality(
        observations,
        reference_time="2026-11-13T09:15:00Z",
        max_age_seconds=3600,
    )

    assert report["observation_count"] == 2
    assert report["review_required_count"] == 0
    assert report["flag_counts"] == {}
    assert all(item["quality_status"] == "ACCEPTABLE" for item in report["observations"])
    assert report["diagnostic_only"] is True
    assert report["score_changed"] is False
    assert report["fraud_determination"] is False


def test_quality_monitor_flags_stale_and_future_observations():
    observations = normalize_signal_observations([
        _observation("SIG-001", "ev-stale", event_key="event-stale", observed_at="2026-11-12T00:00:00Z"),
        _observation("SIG-006", "ev-future", event_key="event-future", observed_at="2026-11-13T10:00:00Z"),
    ])

    report = assess_observation_quality(
        observations,
        reference_time="2026-11-13T09:00:00Z",
        max_age_seconds=3600,
    )

    assert report["flag_counts"] == {"FUTURE_TIMESTAMP": 1, "STALE": 1}
    assert report["observations"][0]["quality_flags"] == ["STALE"]
    assert report["observations"][1]["quality_flags"] == ["FUTURE_TIMESTAMP"]
    assert report["review_required_count"] == 2


def test_quality_monitor_flags_out_of_order_events_without_reordering_or_dropping_them():
    observations = normalize_signal_observations([
        _observation("SIG-001", "ev-later", event_key="event-later", observed_at="2026-11-13T09:10:00Z"),
        _observation("SIG-006", "ev-earlier", event_key="event-earlier", observed_at="2026-11-13T09:05:00Z"),
    ])

    report = assess_observation_quality(
        observations,
        reference_time="2026-11-13T09:15:00Z",
        max_age_seconds=3600,
    )

    assert [item["event_key"] for item in report["observations"]] == ["event-later", "event-earlier"]
    assert report["observations"][0]["quality_flags"] == []
    assert report["observations"][1]["quality_flags"] == ["OUT_OF_ORDER"]


def test_quality_monitor_distinguishes_duplicate_events_from_conflicting_event_keys():
    observations = normalize_signal_observations([
        _observation("SIG-001", "ev-1", event_key="event-1", observed_at="2026-11-13T09:00:00Z"),
        _observation("SIG-001", "ev-1", event_key="event-1", observed_at="2026-11-13T09:00:00Z"),
        _observation("SIG-006", "ev-2", event_key="event-1", observed_at="2026-11-13T09:01:00Z"),
    ])

    report = assess_observation_quality(
        observations,
        reference_time="2026-11-13T09:05:00Z",
        max_age_seconds=3600,
    )

    assert report["flag_counts"] == {
        "CONFLICTING_EVENT_KEY": 1,
        "DUPLICATE_EVENT": 1,
        "DUPLICATE_EVIDENCE_ID": 1,
    }
    assert report["observations"][1]["quality_flags"] == ["DUPLICATE_EVENT", "DUPLICATE_EVIDENCE_ID"]
    assert report["observations"][2]["quality_flags"] == ["CONFLICTING_EVENT_KEY"]


def test_quality_monitor_rejects_naive_timestamps_and_non_synthetic_data():
    observations = normalize_signal_observations([
        _observation("SIG-001", "ev-1", event_key="event-1"),
    ])

    with pytest.raises(ValueError, match="timezone"):
        assess_observation_quality(
            observations,
            reference_time="2026-11-13T09:00:00",
        )

    observations[0]["observed_at"] = "2026-11-13T09:00:00"
    with pytest.raises(ValueError, match="timezone"):
        assess_observation_quality(
            observations,
            reference_time="2026-11-13T09:00:00Z",
        )

    observations[0]["data_mode"] = "bank"
    with pytest.raises(ValueError, match="synthetic data only"):
        assess_observation_quality(
            observations,
            reference_time="2026-11-13T09:00:00Z",
        )
