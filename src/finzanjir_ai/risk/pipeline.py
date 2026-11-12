from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

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


def _validate_threshold_config(threshold_config: dict[str, Any] | None) -> dict[str, Any] | None:
    if threshold_config is None:
        return None
    if not isinstance(threshold_config, dict):
        raise ValueError("threshold_config must be an object")
    required_fields = ("id", "value", "score_scale", "version", "changed_by", "effective_at", "status")
    if any(field not in threshold_config for field in required_fields):
        raise ValueError("threshold_config is missing required fields")
    if threshold_config["score_scale"] != "priority_0_100" or threshold_config["status"] != "ACTIVE":
        raise ValueError("threshold_config must be active and use priority_0_100 scale")
    if not isinstance(threshold_config["id"], str) or not threshold_config["id"].strip():
        raise ValueError("threshold_config id must be a non-empty string")
    if not isinstance(threshold_config["version"], int) or isinstance(threshold_config["version"], bool) or threshold_config["version"] < 1:
        raise ValueError("threshold_config version must be a positive integer")
    if not isinstance(threshold_config["changed_by"], str) or not threshold_config["changed_by"].strip():
        raise ValueError("threshold_config changed_by must be a non-empty string")
    if not isinstance(threshold_config["effective_at"], str) or not threshold_config["effective_at"].strip():
        raise ValueError("threshold_config effective_at must be a non-empty string")
    if not isinstance(threshold_config["value"], (int, float)) or isinstance(threshold_config["value"], bool) or not math.isfinite(threshold_config["value"]) or not 0 <= threshold_config["value"] <= 100:
        raise ValueError("threshold_config value must be between 0 and 100")
    return dict(threshold_config)


def _process_multi_signal_transaction(
    transaction: dict[str, Any],
    *,
    signal_events: list[dict[str, Any]],
    escalation_threshold: float,
    threshold_config: dict[str, Any] | None = None,
) -> PipelineResult:
    shadow_mode = transaction.get("shadow_mode", True)
    if not isinstance(shadow_mode, bool):
        raise ValueError("shadow_mode must be boolean")

    threshold_value = float(threshold_config["value"]) if threshold_config else escalation_threshold * 100
    evaluation = evaluate_signal_set(
        signal_events,
        escalation_threshold=threshold_value,
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

    active_threshold = dict(threshold_config) if threshold_config else {
        "id": "multi-signal-escalation-v1",
        "type": "case_escalation",
        "value": evaluation["threshold"],
        "score_scale": "priority_0_100",
        "version": 1,
        "status": "ACTIVE",
        "effective_at": transaction["occurred_at"],
        "changed_by": "system:default",
        "reason": "Default synthetic threshold.",
        "data_mode": "synthetic",
    }
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
        "threshold_id": active_threshold["id"],
        "threshold_version": active_threshold["version"],
        "threshold_changed_by": active_threshold["changed_by"],
        "threshold_effective_at": active_threshold["effective_at"],
        "threshold": active_threshold,
        "family_contributions": evaluation["family_contributions"],
        "contributions": evaluation["contributions"],
        "deduplicated_evidence_ids": evaluation["deduplicated_evidence_ids"],
        "registry_version": evaluation["registry_version"],
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
            "threshold_id": risk["threshold_id"],
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
    threshold_config: dict[str, Any] | None = None,
) -> PipelineResult:
    transaction = _validate_transaction(transaction)
    threshold_config = _validate_threshold_config(threshold_config)

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

    if "signal_events" in transaction and transaction["signal_events"] is not None:
        return _process_multi_signal_transaction(
            transaction,
            signal_events=transaction["signal_events"],
            escalation_threshold=float(escalation_threshold),
            threshold_config=threshold_config,
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

    # Deprecated compatibility path: a large amount alone is context, not a
    # fraud signal. Keep the old event visible, but assign no risk points and
    # never open a Case from this single attribute.
    signal_id = f"legacy-context-{transaction['transaction_id']}"
    signal = {
        "id": signal_id,
        "signal_id": "LEGACY-LARGE-TRANSACTION-CONTEXT",
        "transaction_id": transaction["transaction_id"],
        "type": "LARGE_TRANSACTION_CONTEXT",
        "source": "synthetic-bank",
        "occurred_at": transaction["occurred_at"],
        "status": "CONTEXT_ONLY",
        "data_mode": "synthetic",
        "scoring_mode": "legacy_demo_context_only",
    }
    evidence = {
        "id": f"legacy-context-evidence-{transaction['transaction_id']}",
        "signal_id": signal_id,
        "type": "TRANSACTION_AMOUNT_CONTEXT",
        "status": "CONTEXT_ONLY",
        "observed_at": transaction["occurred_at"],
        "provenance": {
            "source": "synthetic-bank",
            "transaction_id": transaction["transaction_id"],
            "data_mode": "synthetic",
        },
    }
    active_threshold = threshold_config or {
        "id": "multi-signal-case-escalation",
        "type": "case_escalation",
        "value": 75.0,
        "score_scale": "priority_0_100",
        "version": 1,
        "status": "ACTIVE",
        "effective_at": transaction["occurred_at"],
        "changed_by": "system:default",
        "reason": "Default synthetic threshold.",
        "data_mode": "synthetic",
    }
    risk = {
        "id": f"risk-{transaction['transaction_id']}",
        "signal_id": signal_id,
        "signal_ids": [signal_id],
        "score": 0.0,
        "score_scale": "priority_0_100",
        "threshold_scale": "priority_0_100",
        "level": "OBSERVE",
        "evidence_confidence": 0.0,
        "calculated_at": transaction["occurred_at"],
        "engine_version": "multi-signal-shadow-v1",
        "registry_version": "signal-registry-v1",
        "threshold_met": False,
        "case_eligible": False,
        "case_block_reason": "single_amount_context_not_sufficient",
        "case_suppressed_reason": "legacy_demo_context_only",
        "evidence_count": 0,
        "independent_families": 0,
        "escalation_threshold": float(active_threshold["value"]),
        "threshold_id": active_threshold["id"],
        "threshold_version": active_threshold["version"],
        "threshold_changed_by": active_threshold["changed_by"],
        "threshold_effective_at": active_threshold["effective_at"],
        "threshold": dict(active_threshold),
        "family_contributions": {},
        "contributions": [],
        "deduplicated_evidence_ids": [],
        "score_semantics": "context_only_not_risk_score",
        "scoring_mode": "legacy_demo_context_only",
        "data_mode": "synthetic",
        "shadow_mode": True,
    }
    return PipelineResult(
        signal=signal,
        evidence=evidence,
        risk=risk,
        case=None,
        signals=(signal,),
        evidences=(evidence,),
    )
