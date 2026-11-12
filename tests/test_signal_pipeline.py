import math

import pytest

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


def test_pipeline_rejects_missing_required_transaction_fields():
    transaction = {
        "bank_id": "bank-demo",
        "actor_id": "actor-102",
        "amount": 2500,
        "currency": "UZS",
        "occurred_at": "2026-11-11T00:00:03Z",
        "channel": "mobile",
        "status": "AUTHORIZED",
        "synthetic": True,
    }

    with pytest.raises(ValueError, match="transaction_id"):
        process_transaction(
            transaction,
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )


@pytest.mark.parametrize("amount", [math.nan, math.inf, -math.inf, "2500"])
def test_pipeline_rejects_invalid_transaction_amounts(amount):
    transaction = {
        "transaction_id": "syn-tx-103",
        "bank_id": "bank-demo",
        "actor_id": "actor-103",
        "amount": amount,
        "currency": "UZS",
        "occurred_at": "2026-11-11T00:00:04Z",
        "channel": "mobile",
        "status": "AUTHORIZED",
        "synthetic": True,
    }

    with pytest.raises(ValueError, match="amount"):
        process_transaction(
            transaction,
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "1000"])
def test_pipeline_rejects_invalid_signal_amount_thresholds(value):
    with pytest.raises(ValueError, match="signal_amount_threshold"):
        process_transaction(
            {
                "transaction_id": "syn-tx-104",
                "bank_id": "bank-demo",
                "actor_id": "actor-104",
                "amount": 2500,
                "currency": "UZS",
                "occurred_at": "2026-11-11T00:00:05Z",
                "channel": "mobile",
                "status": "AUTHORIZED",
                "synthetic": True,
            },
            signal_amount_threshold=value,
            escalation_threshold=0.75,
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "0.75"])
def test_pipeline_rejects_invalid_escalation_thresholds(value):
    with pytest.raises(ValueError, match="escalation_threshold"):
        process_transaction(
            {
                "transaction_id": "syn-tx-105",
                "bank_id": "bank-demo",
                "actor_id": "actor-105",
                "amount": 2500,
                "currency": "UZS",
                "occurred_at": "2026-11-11T00:00:06Z",
                "channel": "mobile",
                "status": "AUTHORIZED",
                "synthetic": True,
            },
            signal_amount_threshold=1000,
            escalation_threshold=value,
        )
