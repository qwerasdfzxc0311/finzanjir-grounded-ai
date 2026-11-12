import pytest

from finzanjir_ai.risk.registry import SIGNAL_REGISTRY
from finzanjir_ai.risk.scoring import evaluate_signal_set


def _event(signal_id: str, evidence_id: str, **overrides):
    event = {
        "signal_id": signal_id,
        "evidence_id": evidence_id,
        "source": "synthetic-test",
        "observed_at": "2026-11-12T09:00:00Z",
        "evidence_quality": 1.0,
        "recency_factor": 1.0,
    }
    event.update(overrides)
    return event


def test_registry_contains_fifteen_legacy_and_twenty_candidate_signals():
    legacy = [item for item in SIGNAL_REGISTRY.values() if item.source_status == "legacy"]
    candidate = [item for item in SIGNAL_REGISTRY.values() if item.source_status == "candidate"]

    assert len(legacy) == 15
    assert len(candidate) == 25
    assert len(SIGNAL_REGISTRY) == 40


def test_multi_signal_score_requires_independent_families_and_evidence():
    result = evaluate_signal_set([
        _event("SIG-018", "ev-auth"),
        _event("SIG-006", "ev-device"),
        _event("SIG-012", "ev-account"),
        _event("SIG-004", "ev-beneficiary"),
        _event("SIG-002", "ev-velocity"),
    ])

    assert result["score"] == 80
    assert result["risk_level"] == "HIGH"
    assert result["independent_families"] == 5
    assert result["evidence_count"] == 5
    assert result["case_eligible"] is True
    assert result["score_semantics"] == "priority_score_not_probability_or_guilt"
    assert result["registry_version"] == "signal-registry-v1"


def test_related_auth_signals_are_limited_by_family_cap():
    result = evaluate_signal_set([
        _event("SIG-016", "ev-auth-1"),
        _event("SIG-017", "ev-auth-2"),
        _event("SIG-018", "ev-auth-3"),
    ])

    assert result["score"] == 30
    assert result["family_contributions"]["AUTH"] == 30
    assert result["independent_families"] == 1
    assert result["case_eligible"] is False
    assert result["case_block_reason"] == "threshold_not_met"


def test_same_evidence_cannot_be_counted_twice():
    result = evaluate_signal_set([
        _event("SIG-006", "same-evidence"),
        _event("SIG-035", "same-evidence"),
    ])

    assert result["score"] == 15
    assert result["evidence_count"] == 1
    assert result["deduplicated_evidence_ids"] == ["same-evidence"]


def test_evidence_quality_and_recency_reduce_contribution():
    result = evaluate_signal_set([
        _event("SIG-012", "ev-weak", evidence_quality=0.5, recency_factor=0.5),
    ])

    assert result["score"] == 5
    assert result["evidence_confidence"] == 0.5
    assert result["case_eligible"] is False


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -0.1, 1.1, "1"])
def test_signal_event_rejects_invalid_evidence_quality(bad):
    with pytest.raises(ValueError, match="evidence_quality"):
        evaluate_signal_set([_event("SIG-006", "ev-bad", evidence_quality=bad)])


def test_signal_event_rejects_unknown_signal_and_missing_provenance():
    with pytest.raises(ValueError, match="unknown signal_id"):
        evaluate_signal_set([_event("SIG-999", "ev-unknown")])

    with pytest.raises(ValueError, match="source"):
        evaluate_signal_set([_event("SIG-006", "ev-no-source", source="")])


def test_threshold_and_minimum_support_are_validated():
    with pytest.raises(ValueError, match="escalation_threshold"):
        evaluate_signal_set([], escalation_threshold=101)

    with pytest.raises(ValueError, match="minimum_independent_families"):
        evaluate_signal_set([], minimum_independent_families=0)



@pytest.mark.parametrize("signal_id", sorted(SIGNAL_REGISTRY))
def test_every_registered_signal_has_a_synthetic_evidence_test_path(signal_id):
    definition = SIGNAL_REGISTRY[signal_id]
    result = evaluate_signal_set([_event(signal_id, f"ev-{signal_id}")])

    assert result["evidence_count"] == 1
    assert result["contributions"][0]["signal_id"] == signal_id
    if not definition.score_eligible:
        assert result["score"] == 0
        assert result["contributions"][0]["score_suppressed_reason"] == "context_only"
    elif definition.requires_corroboration:
        assert result["score"] == 0
        assert result["contributions"][0]["score_suppressed_reason"] == "requires_corroboration"
    else:
        assert result["score"] == definition.weight


def test_micro_transaction_candidate_scores_only_with_a_distinct_corroborating_signal():
    result = evaluate_signal_set([
        _event("SIG-036", "ev-micro", corroborating_signal_ids=["SIG-002"]),
        _event("SIG-002", "ev-follow-up"),
    ])

    assert result["score"] == 20
    assert result["contributions"][0]["score_eligible"] is True


@pytest.mark.parametrize("signal_id", ["SIG-038", "SIG-040"])
def test_context_only_small_signals_never_add_risk_points(signal_id):
    result = evaluate_signal_set([_event(signal_id, f"ev-{signal_id}")])

    assert result["score"] == 0
    assert result["independent_families"] == 0
    assert result["case_eligible"] is False



def test_evidence_deduplication_is_order_independent():
    first = evaluate_signal_set([
        _event("SIG-035", "shared-device-evidence"),
        _event("SIG-006", "shared-device-evidence"),
    ])
    second = evaluate_signal_set([
        _event("SIG-006", "shared-device-evidence"),
        _event("SIG-035", "shared-device-evidence"),
    ])

    assert first["score"] == second["score"] == 15
    assert first["contributions"][0]["signal_id"] == "SIG-006"
    assert second["contributions"][0]["signal_id"] == "SIG-006"


def test_corroboration_must_use_a_different_evidence_item():
    result = evaluate_signal_set([
        _event("SIG-036", "same-event", corroborating_signal_ids=["SIG-002"]),
        _event("SIG-002", "same-event"),
    ])

    assert result["score"] == 15
    assert result["evidence_count"] == 1
    assert result["contributions"][0]["signal_id"] == "SIG-002"


def test_signal_event_count_is_bounded():
    with pytest.raises(ValueError, match="100 items"):
        evaluate_signal_set([_event("SIG-006", f"ev-{index}") for index in range(101)])


@pytest.mark.parametrize("observed_at", [
    "2026-11-12T09:00:00",
    "2026-13-40T09:00:00Z",
    "not-a-timestamp",
])
def test_signal_event_requires_valid_timezone_aware_iso_timestamp(observed_at):
    with pytest.raises(ValueError, match="observed_at"):
        evaluate_signal_set([_event("SIG-006", "ev-bad-time", observed_at=observed_at)])


def test_signal_event_rejects_unknown_or_duplicate_corroboration_references():
    with pytest.raises(ValueError, match="corroborating_signal_ids"):
        evaluate_signal_set([
            _event("SIG-036", "ev-micro", corroborating_signal_ids=["SIG-999"]),
        ])
    with pytest.raises(ValueError, match="corroborating_signal_ids"):
        evaluate_signal_set([
            _event("SIG-036", "ev-micro", corroborating_signal_ids=["SIG-002", "SIG-002"]),
        ])


def test_distinct_evidence_ids_from_the_same_source_event_are_deduplicated():
    result = evaluate_signal_set([
        _event("SIG-006", "ev-device-a", event_key="source-event-42"),
        _event("SIG-035", "ev-device-b", event_key="source-event-42"),
    ])

    assert result["score"] == 15
    assert result["evidence_count"] == 1
    assert result["independent_families"] == 1
    assert result["deduplicated_event_keys"] == ["source-event-42"]
    assert result["deduplicated_evidence_ids"] == ["ev-device-a", "ev-device-b"]
    assert result["contributions"][0]["signal_id"] == "SIG-006"


def test_same_source_event_cannot_self_corroborate_across_different_evidence_ids():
    result = evaluate_signal_set([
        _event("SIG-036", "ev-micro", event_key="same-source-event", corroborating_signal_ids=["SIG-002"]),
        _event("SIG-002", "ev-follow-up", event_key="same-source-event"),
    ])

    assert result["evidence_count"] == 1
    assert result["score"] == 15
    assert result["contributions"][0]["signal_id"] == "SIG-002"


def test_evidence_id_cannot_be_reassigned_to_another_source_event():
    with pytest.raises(ValueError, match="multiple event_key"):
        evaluate_signal_set([
            _event("SIG-006", "same-evidence", event_key="event-a"),
            _event("SIG-035", "same-evidence", event_key="event-b"),
        ])


def test_source_event_key_must_be_a_bounded_opaque_identifier():
    with pytest.raises(ValueError, match="event_key"):
        evaluate_signal_set([_event("SIG-006", "ev-space", event_key="raw customer name")])
    with pytest.raises(ValueError, match="event_key"):
        evaluate_signal_set([_event("SIG-006", "ev-long", event_key="x" * 257)])



def test_same_signal_duplicate_source_event_tie_break_is_order_independent():
    first_event = _event(
        "SIG-006",
        "ev-z",
        event_key="shared-source-event",
        source="source-z",
    )
    second_event = _event(
        "SIG-006",
        "ev-a",
        event_key="shared-source-event",
        source="source-a",
    )

    forward = evaluate_signal_set([first_event, second_event])
    reverse = evaluate_signal_set([second_event, first_event])

    assert forward["score"] == reverse["score"] == 15
    assert forward["evidence_count"] == reverse["evidence_count"] == 1
    assert forward["contributions"] == reverse["contributions"]
    assert forward["contributions"][0]["evidence_id"] == "ev-a"
    assert forward["contributions"][0]["source"] == "source-a"
