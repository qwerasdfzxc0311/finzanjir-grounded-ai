import pytest

from finzanjir_ai.transaction_chain.correlation import TransactionChainCorrelator


def test_case_chain_requires_source_time_and_correlation_reason():
    correlator = TransactionChainCorrelator()

    with pytest.raises(ValueError, match="source"):
        correlator.correlate([
            {
                "event_id": "event-1",
                "transaction_id": "tx-1",
                "source": "",
                "occurred_at": "2026-11-12T07:00:00Z",
                "correlation_reason": "same transaction",
            }
        ])

    with pytest.raises(ValueError, match="occurred_at"):
        correlator.correlate([
            {
                "event_id": "event-1",
                "transaction_id": "tx-1",
                "source": "risk_pipeline",
                "occurred_at": "",
                "correlation_reason": "same transaction",
            }
        ])

    with pytest.raises(ValueError, match="correlation_reason"):
        correlator.correlate([
            {
                "event_id": "event-1",
                "transaction_id": "tx-1",
                "source": "risk_pipeline",
                "occurred_at": "2026-11-12T07:00:00Z",
                "correlation_reason": "",
            }
        ])


def test_incomplete_chain_cannot_be_presented_as_final_proof():
    correlator = TransactionChainCorrelator()

    result = correlator.correlate(
        [
            {
                "event_id": "event-1",
                "transaction_id": "tx-1",
                "source": "risk_pipeline",
                "occurred_at": "2026-11-12T07:00:00Z",
                "correlation_reason": "same transaction",
            },
            {
                "event_id": "event-2",
                "transaction_id": "tx-1",
                "source": "case_manager",
                "occurred_at": "",
                "correlation_reason": "case opened from risk escalation",
            },
        ],
        allow_incomplete=True,
    )

    assert result["complete"] is False
    assert result["final_proof"] is False
    assert result["incomplete_event_ids"] == ["event-2"]


def test_complete_chain_exposes_source_time_reason_and_is_final_proof_eligible():
    correlator = TransactionChainCorrelator()

    result = correlator.correlate(
        [
            {
                "event_id": "event-1",
                "transaction_id": "tx-1",
                "source": "risk_pipeline",
                "occurred_at": "2026-11-12T07:00:00Z",
                "correlation_reason": "same transaction",
            },
            {
                "event_id": "event-2",
                "transaction_id": "tx-1",
                "source": "case_manager",
                "occurred_at": "2026-11-12T07:00:01Z",
                "correlation_reason": "case opened from risk escalation",
            },
        ]
    )

    assert result["complete"] is True
    assert result["final_proof"] is True
    assert result["events"][1]["source"] == "case_manager"
    assert result["events"][1]["occurred_at"] == "2026-11-12T07:00:01Z"
    assert result["events"][1]["correlation_reason"] == "case opened from risk escalation"
