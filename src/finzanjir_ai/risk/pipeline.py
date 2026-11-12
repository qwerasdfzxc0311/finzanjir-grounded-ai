from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .engine import evaluate_risk
from .scoring import evaluate_signal_set


@dataclass(frozen=True)
class PipelineResult:
    signal: dict[str, Any] | None
    evidence: dict[str, Any] | None
    risk: dict[str, Any] | None
    case: dict[str, Any] | None
    signals: tuple[dict[str, Any], ...] = ()
    evidences: tuple[dict[str, Any], ...] = ()


def _validate_transaction(transaction: Any) -> dict[str, Any]:
    if not isinstance(transaction, dict):
        raise ValueError("transaction must be an object")
    if transaction.get("synthetic") is not True:
        raise ValueError("Signal/Risk prototype pipeline accepts only explicitly synthetic transactions")
    for field in ("transaction_id", "bank_id", "actor_id", "occurred_at"):
        value = transaction.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"transaction {field} must be a non-empty string")
    return transaction


def _process_multi_signal_transaction(
    transaction: dict[str, Any],
    *,
    signal_events: list[dict[str, Any]],
    escalation_threshold: float,
) -> PipelineResult:
    shadow_mode = transaction.get("shadow_mode", True)
    if not isinstance(shadow_mode, bool):
        raise ValueError("shadow_mode must be boolean")

    evaluation = evaluate_signal_set(
        signal_events,
        escalation_threshold=escalation_threshold * 100,
    )
    signals = tuple(
        {
            "id": f"signal-{item['signal_id'].lower()}-{item['evidence_id']}",
            "signal_id": item["signal_id"],
            "transaction_id": transaction["transaction_id"],
            "type": item["signal_id"],
            "family": item["family"],
            "source": item["source"],
            "occurred_at": item["observed_at"],
            "status": "ACTIVE",
            "data_mode": "synthetic",
        }
        for item in evaluation["contributions"]
    )
    evidences = tuple(
        {
            "id": item["evidence_id"],
            "signal_id": f"signal-{item['signal_id'].lower()}-{item['evidence_id']}",
            "type": "SIGNAL_EVIDENCE",
            "status": "OBSERVED",
            "observed_at": item["observed_at"],
            "evidence_quality": item["evidence_quality"],
            "recency_factor": item["recency_factor"],
            "provenance": {
                "source": item["source"],
                "transaction_id": transaction["transaction_id"],
                "data_mode": "synthetic",
            },
        }
        for item in evaluation["contributions"]
    )

    risk = {
        "id": f"risk-{transaction['transaction_id']}",
        "signal_ids": [item["id"] for item in signals],
        "score": evaluation["score"],
        "score_scale": "priority_0_100",
        "threshold_scale": "priority_0_100",
        "level": evaluation["risk_level"],
        "evidence_confidence": evaluation["evidence_confidence"],
        "calculated_at": transaction["occurred_at"],
        "engine_version": evaluation["engine_version"],
        "threshold_met": evaluation["threshold_met"],
        "case_eligible": evaluation["case_eligible"],
        "case_block_reason": evaluation["case_block_reason"],
        "case_suppressed_reason": "shadow_mode" if shadow_mode and evaluation["case_eligible"] else None,
        "evidence_count": evaluation["evidence_count"],
        "independent_families": evaluation["independent_families"],
        "escalation_threshold": evaluation["threshold"],
        "family_contributions": evaluation["family_contributions"],
        "contributions": evaluation["contributions"],
        "deduplicated_evidence_ids": evaluation["deduplicated_evidence_ids"],
        "score_semantics": evaluation["score_semantics"],
        "data_mode": "synthetic",
        "shadow_mode": shadow_mode,
    }

    case = None
    if evaluation["case_eligible"] and not shadow_mode:
        case = {
            "id": f"case-{transaction['transaction_id']}",
            "bank_id": transaction["bank_id"],
            "citizen_id": transaction.get("citizen_id", "synthetic-subject"),
            "transaction_id": transaction["transaction_id"],
            "signal_ids": [item["id"] for item in signals],
            "risk_id": risk["id"],
            "threshold_id": "multi-signal-escalation-v1",
            "status": "OPEN",
            "opened_at": transaction["occurred_at"],
            "data_mode": "synthetic",
        }

    return PipelineResult(
        signal=signals[0] if signals else None,
        evidence=evidences[0] if evidences else None,
        risk=risk,
        case=case,
        signals=signals,
        evidences=evidences,
    )


def process_transaction(
    transaction: dict[str, Any],
    *,
    signal_amount_threshold: float,
    escalation_threshold: float,
) -> PipelineResult:
    transaction = _validate_transaction(transaction)

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

    # New evidence-backed multi-signal mode. Missing signal_events preserves the
    # legacy synthetic demo path until the connected demo fixtures are migrated.
    if "signal_events" in transaction and transaction["signal_events"] is not None:
        return _process_multi_signal_transaction(
            transaction,
            signal_events=transaction["signal_events"],
            escalation_threshold=float(escalation_threshold),
        )

    amount = transaction.get("amount")
    if (
        not isinstance(amount, (int, float))
        or isinstance(amount, bool)
        or not math.isfinite(amount)
    ):
        raise ValueError("transaction amount must be finite")

    if amount < signal_amount_threshold:
        return PipelineResult(signal=None, evidence=None, risk=None, case=None)

    signal = {
        "id": f"sig-{transaction['transaction_id']}",
        "transaction_id": transaction["transaction_id"],
        "type": "LARGE_TRANSACTION",
        "source": "synthetic-bank",
        "occurred_at": transaction["occurred_at"],
        "status": "ACTIVE",
        "data_mode": "synthetic",
        "scoring_mode": "legacy_demo_compatibility",
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
        "signal_ids": [signal["id"]],
        "score": evaluation.signal_score,
        "score_scale": "legacy_0_1",
        "threshold_scale": "legacy_0_1",
        "level": evaluation.risk_level,
        "calculated_at": transaction["occurred_at"],
        "engine_version": "risk-v1-legacy-demo",
        "threshold_met": evaluation.threshold_met,
        "case_eligible": evaluation.case_should_open,
        "independent_families": 1,
        "evidence_count": evaluation.evidence_count,
        "escalation_threshold": escalation_threshold,
        "scoring_mode": "legacy_demo_compatibility",
        "score_semantics": "legacy_demo_score_not_probability",
        "shadow_mode": False,
        "data_mode": "synthetic",
    }

    case = None
    if evaluation.case_should_open:
        case = {
            "id": f"case-{transaction['transaction_id']}",
            "bank_id": transaction["bank_id"],
            "citizen_id": transaction.get("citizen_id", "synthetic-subject"),
            "transaction_id": transaction["transaction_id"],
            "signal_ids": [signal["id"]],
            "risk_id": risk["id"],
            "threshold_id": "case-escalation-v1",
            "status": "OPEN",
            "opened_at": transaction["occurred_at"],
            "data_mode": "synthetic",
        }

    return PipelineResult(
        signal=signal,
        evidence=evidence,
        risk=risk,
        case=case,
        signals=(signal,),
        evidences=(evidence,),
    )
