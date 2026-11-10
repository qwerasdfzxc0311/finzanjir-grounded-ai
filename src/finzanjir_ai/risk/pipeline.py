from __future__ import annotations

from dataclasses import dataclass
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
    if transaction.get("synthetic") is not True:
        raise ValueError("Signal/Risk prototype pipeline accepts only explicitly synthetic transactions")

    if transaction["amount"] < signal_amount_threshold:
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

    evaluation = evaluate_risk(signal_score=0.85, evidence_count=1, escalation_threshold=escalation_threshold)
    risk = {
        "id": f"risk-{transaction['transaction_id']}",
        "signal_id": signal["id"],
        "score": evaluation.score if hasattr(evaluation, "score") else evaluation.signal_score,
        "level": evaluation.risk_level,
        "calculated_at": transaction["occurred_at"],
        "engine_version": "risk-v1",
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
