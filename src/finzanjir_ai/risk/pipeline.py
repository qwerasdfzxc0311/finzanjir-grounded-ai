from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .engine import evaluate_risk


@dataclass(frozen=True)
class PipelineResult:
    signal: dict[str, Any] | None
    evidence: dict[str, Any] | None
    risk: dict[str, Any] | None
    case: dict[str, Any] | None


def process_transaction(
    transaction: dict[str, Any],
    *,
    signal_amount_threshold: float,
    escalation_threshold: float,
) -> PipelineResult:
    if not isinstance(transaction, dict):
        raise ValueError("transaction must be an object")

    if transaction.get("synthetic") is not True:
        raise ValueError("Signal/Risk prototype pipeline accepts only explicitly synthetic transactions")

    for field in ("transaction_id", "bank_id", "actor_id", "occurred_at"):
        value = transaction.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"transaction {field} must be a non-empty string")

    amount = transaction.get("amount")
    if (
        not isinstance(amount, (int, float))
        or isinstance(amount, bool)
        or not math.isfinite(amount)
    ):
        raise ValueError("transaction amount must be finite")

    if (
        not isinstance(signal_amount_threshold, (int, float))
        or isinstance(signal_amount_threshold, bool)
        or not math.isfinite(signal_amount_threshold)
    ):
        raise ValueError("signal_amount_threshold must be finite")
    if signal_amount_threshold < 0:
        raise ValueError("signal_amount_threshold must be non-negative")

    if (
        not isinstance(escalation_threshold, (int, float))
        or isinstance(escalation_threshold, bool)
        or not math.isfinite(escalation_threshold)
    ):
        raise ValueError("escalation_threshold must be finite")
    if not 0 <= escalation_threshold <= 1:
        raise ValueError("escalation_threshold must be between 0 and 1")

    if amount < signal_amount_threshold:
        return PipelineResult(signal=None, evidence=None, risk=None, case=None)

    signal = {
        "id": f"sig-{transaction['transaction_id']}",
        "transaction_id": transaction["transaction_id"],
        "type": "LARGE_TRANSACTION",
        "source": "synthetic-bank",
        "occurred_at": transaction["occurred_at"],
        "status": "ACTIVE",
    }
    evidence = {
        "id": f"ev-{transaction['transaction_id']}",
        "signal_id": signal["id"],
        "type": "TRANSACTION_AMOUNT",
        "status": "OBSERVED",
        "observed_at": transaction["occurred_at"],
        "provenance": {"source": "synthetic-bank", "transaction_id": transaction["transaction_id"]},
    }

    evaluation = evaluate_risk(
        signal_score=0.85,
        evidence_count=1,
        escalation_threshold=escalation_threshold,
    )
    risk = {
        "id": f"risk-{transaction['transaction_id']}",
        "signal_id": signal["id"],
        "score": evaluation.score if hasattr(evaluation, "score") else evaluation.signal_score,
        "level": evaluation.risk_level,
        "calculated_at": transaction["occurred_at"],
        "engine_version": "risk-v1",
        "threshold_met": evaluation.threshold_met,
        "evidence_count": evaluation.evidence_count,
        "escalation_threshold": escalation_threshold,
    }

    case = None
    if evaluation.case_should_open:
        case = {
            "id": f"case-{transaction['transaction_id']}",
            "signal_ids": [signal["id"]],
            "risk_id": risk["id"],
            "threshold_id": "case-escalation-v1",
            "status": "OPEN",
            "opened_at": transaction["occurred_at"],
        }

    return PipelineResult(signal=signal, evidence=evidence, risk=risk, case=case)
