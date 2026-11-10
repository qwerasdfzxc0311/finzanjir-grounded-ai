from finzanjir_ai.risk.pipeline import process_transaction


def test_transaction_above_signal_threshold_flows_to_risk_and_case():
    result = process_transaction(
        {
            "transaction_id": "syn-tx-100",
            "bank_id": "bank-demo",
            "actor_id": "actor-100",
            "amount": 2500,
            "currency": "UZS",
            "occurred_at": "2026-11-11T00:00:01Z",
            "channel": "mobile",
            "status": "AUTHORIZED",
            "synthetic": True,
        },
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert result.signal is not None
    assert result.evidence is not None
    assert result.risk is not None
    assert result.case is not None
    assert result.case["status"] == "OPEN"


def test_transaction_below_signal_threshold_stops_before_case():
    result = process_transaction(
        {
            "transaction_id": "syn-tx-101",
            "bank_id": "bank-demo",
            "actor_id": "actor-101",
            "amount": 100,
            "currency": "UZS",
            "occurred_at": "2026-11-11T00:00:02Z",
            "channel": "card",
            "status": "AUTHORIZED",
            "synthetic": True,
        },
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert result.signal is None
    assert result.evidence is None
    assert result.risk is None
    assert result.case is None
