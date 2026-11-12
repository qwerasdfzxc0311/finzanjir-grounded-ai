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
    assert len(candidate) == 20
    assert len(SIGNAL_REGISTRY) == 35


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
    assert result["case_block_reason"] == "insufficient_independent_evidence"


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
