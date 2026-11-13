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
    assert result["chain_metadata_complete"] is True
    assert result["final_proof"] is False
    assert result["proof_scope"] == "single_transaction_event_metadata_completeness_only_not_fraud_or_guilt"
    assert result["events"][1]["source"] == "case_manager"
    assert result["events"][1]["occurred_at"] == "2026-11-12T07:00:01Z"
    assert result["events"][1]["correlation_reason"] == "case opened from risk escalation"


def _synthetic_event(event_id, transaction_id, occurred_at):
    return {
        "event_id": event_id,
        "transaction_id": transaction_id,
        "source": "synthetic_detector",
        "occurred_at": occurred_at,
        "correlation_reason": "synthetic scenario relation",
        "data_mode": "synthetic",
    }


def _synthetic_link(link_id, source_id, target_id, occurred_at):
    return {
        "link_id": link_id,
        "from_transaction_id": source_id,
        "to_transaction_id": target_id,
        "relation_type": "TRANSFER",
        "source": "synthetic_chain_builder",
        "occurred_at": occurred_at,
        "correlation_reason": "explicit synthetic transfer edge",
        "data_mode": "synthetic",
    }


def test_synthetic_multi_transaction_graph_is_connected_without_claiming_guilt():
    result = TransactionChainCorrelator().correlate_synthetic_graph(
        [
            _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z"),
            _synthetic_event("event-2", "tx-2", "2026-11-12T09:01:00Z"),
            _synthetic_event("event-3", "tx-3", "2026-11-12T09:02:00Z"),
        ],
        [
            _synthetic_link("link-1", "tx-1", "tx-2", "2026-11-12T09:01:00Z"),
            _synthetic_link("link-2", "tx-2", "tx-3", "2026-11-12T09:02:00Z"),
        ],
    )

    assert result["status"] == "COMPLETE"
    assert result["chain_complete"] is True
    assert result["connected"] is True
    assert result["components"] == [["tx-1", "tx-2", "tx-3"]]
    assert result["proof_scope"] == "synthetic_transaction_connectivity_only_not_fraud_or_guilt"
    assert result["final_proof"] is False


def test_synthetic_graph_reports_disconnected_components_without_joining_them():
    result = TransactionChainCorrelator().correlate_synthetic_graph(
        [
            _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z"),
            _synthetic_event("event-2", "tx-2", "2026-11-12T09:01:00Z"),
            _synthetic_event("event-3", "tx-3", "2026-11-12T09:02:00Z"),
        ],
        [_synthetic_link("link-1", "tx-1", "tx-2", "2026-11-12T09:01:00Z")],
    )

    assert result["status"] == "DISCONNECTED"
    assert result["chain_complete"] is False
    assert result["components"] == [["tx-1", "tx-2"], ["tx-3"]]
    assert result["final_proof"] is False


def test_synthetic_graph_incomplete_metadata_cannot_be_marked_complete():
    events = [
        _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z"),
        _synthetic_event("event-2", "tx-2", "2026-11-12T09:01:00Z"),
    ]
    events[1]["source"] = ""
    result = TransactionChainCorrelator().correlate_synthetic_graph(
        events,
        [_synthetic_link("link-1", "tx-1", "tx-2", "2026-11-12T09:01:00Z")],
        allow_incomplete=True,
    )

    assert result["status"] == "INCOMPLETE"
    assert result["chain_complete"] is False
    assert result["incomplete_event_ids"] == ["event-2"]
    assert result["final_proof"] is False


def test_synthetic_graph_rejects_unknown_link_endpoints_and_raw_identifiers():
    correlator = TransactionChainCorrelator()
    events = [_synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z")]

    with pytest.raises(ValueError, match="unknown transaction"):
        correlator.correlate_synthetic_graph(
            events,
            [_synthetic_link("link-1", "tx-1", "tx-unknown", "2026-11-12T09:01:00Z")],
        )

    raw_identifier_event = _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z")
    raw_identifier_event["account_number"] = "1234567890"
    with pytest.raises(ValueError, match="unsupported fields"):
        correlator.correlate_synthetic_graph([raw_identifier_event], [])


def test_synthetic_graph_rejects_non_synthetic_scope_duplicate_ids_and_self_links():
    correlator = TransactionChainCorrelator()
    first = _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z")
    second = _synthetic_event("event-2", "tx-2", "2026-11-12T09:01:00Z")

    non_synthetic = dict(second, data_mode="bank")
    with pytest.raises(ValueError, match="data_mode"):
        correlator.correlate_synthetic_graph([first, non_synthetic], [], allow_incomplete=True)

    with pytest.raises(ValueError, match="duplicate event_id"):
        correlator.correlate_synthetic_graph([first, dict(first)], [])

    with pytest.raises(ValueError, match="itself"):
        correlator.correlate_synthetic_graph(
            [first],
            [_synthetic_link("link-1", "tx-1", "tx-1", "2026-11-12T09:01:00Z")],
        )


def test_synthetic_graph_rejects_timezone_free_timestamps_and_duplicate_link_ids():
    correlator = TransactionChainCorrelator()
    events = [
        _synthetic_event("event-1", "tx-1", "2026-11-12T09:00:00Z"),
        _synthetic_event("event-2", "tx-2", "2026-11-12T09:01:00Z"),
    ]
    bad_time = _synthetic_link("link-1", "tx-1", "tx-2", "2026-11-12T09:01:00")
    with pytest.raises(ValueError, match="timezone"):
        correlator.correlate_synthetic_graph(events, [bad_time])

    link = _synthetic_link("link-1", "tx-1", "tx-2", "2026-11-12T09:01:00Z")
    with pytest.raises(ValueError, match="duplicate link_id"):
        correlator.correlate_synthetic_graph(events, [link, dict(link)])
