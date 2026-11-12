import pytest

from finzanjir_ai.risk.pipeline import process_transaction


def _observations(transaction_id):
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
            "condition_met": True,
            "evidence_id": f"{transaction_id}-{suffix}",
            "source": "synthetic-bank-adapter",
            "observed_at": "2026-11-12T09:00:00Z",
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
            "rule_version": "bank-rule-v1",
            "detector_version": "adapter-v1",
            "scope": "bank_internal",
            "data_mode": "synthetic",
        }
        for signal_id, suffix in definitions
    ]


def test_pipeline_consumes_observations_and_preserves_detector_provenance():
    result = process_transaction(
        {
            "transaction_id": "TX-OBS-001",
            "bank_id": "bank-a",
            "actor_id": "actor-observation",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "signal_observations": _observations("TX-OBS-001"),
            "shadow_mode": True,
        },
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert result.risk["score"] == 80
    assert result.risk["case_eligible"] is True
    assert result.risk["shadow_mode"] is True
    assert result.risk["case_suppressed_reason"] == "shadow_mode"
    assert result.case is None
    assert len(result.signals) == 5
    assert all(signal["rule_version"] == "bank-rule-v1" for signal in result.signals)
    assert all(evidence["provenance"]["detector_version"] == "adapter-v1" for evidence in result.evidences)


def test_pipeline_rejects_ambiguous_signal_events_and_observations():
    with pytest.raises(ValueError, match="not both"):
        process_transaction(
            {
                "transaction_id": "TX-OBS-BOTH",
                "bank_id": "bank-a",
                "actor_id": "actor-observation",
                "amount": 2500,
                "occurred_at": "2026-11-12T09:00:00Z",
                "synthetic": True,
                "signal_events": [],
                "signal_observations": [],
            },
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )
