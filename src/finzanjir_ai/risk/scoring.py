from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .registry import FAMILY_CAPS, REGISTRY_VERSION, SIGNAL_REGISTRY


def _unit_interval(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    if not 0 <= value <= 1:
        raise ValueError(f"{field} must be between 0 and 1")
    return float(value)


def evaluate_signal_set(
    signal_events: list[dict[str, Any]],
    *,
    escalation_threshold: float = 75,
    minimum_independent_families: int = 2,
    minimum_evidence_count: int = 2,
) -> dict[str, Any]:
    """Score a set of evidence-backed signals; this is not a fraud probability.

    Each event requires signal_id, evidence_id, source, observed_at,
    evidence_quality and recency_factor. Reused evidence_id values are
    deduplicated so one underlying item cannot contribute more than once.
    """
    if not isinstance(signal_events, list):
        raise ValueError("signal_events must be a list")
    if not isinstance(escalation_threshold, (int, float)) or isinstance(escalation_threshold, bool) or not math.isfinite(escalation_threshold):
        raise ValueError("escalation_threshold must be finite")
    if not 0 <= escalation_threshold <= 100:
        raise ValueError("escalation_threshold must be between 0 and 100")
    for field, value in (
        ("minimum_independent_families", minimum_independent_families),
        ("minimum_evidence_count", minimum_evidence_count),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{field} must be a positive integer")

    event_signal_ids: set[str] = set()
    for index, event in enumerate(signal_events):
        if not isinstance(event, dict):
            raise ValueError(f"signal_events[{index}] must be an object")
        signal_id = event.get("signal_id")
        if not isinstance(signal_id, str) or signal_id not in SIGNAL_REGISTRY:
            raise ValueError(f"unknown signal_id at index {index}")
        event_signal_ids.add(signal_id)

    seen_evidence: set[str] = set()
    contributions: list[dict[str, Any]] = []
    deduplicated: list[str] = []
    family_totals: dict[str, float] = defaultdict(float)
    quality_values: list[float] = []

    for index, event in enumerate(signal_events):
        if not isinstance(event, dict):
            raise ValueError(f"signal_events[{index}] must be an object")
        signal_id = event.get("signal_id")
        definition = SIGNAL_REGISTRY.get(signal_id) if isinstance(signal_id, str) else None
        if definition is None:
            raise ValueError(f"unknown signal_id at index {index}")
        for field in ("evidence_id", "source", "observed_at"):
            value = event.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"signal_events[{index}].{field} must be a non-empty string")

        evidence_id = event["evidence_id"].strip()
        if evidence_id in seen_evidence:
            deduplicated.append(evidence_id)
            continue
        seen_evidence.add(evidence_id)

        quality = _unit_interval(event.get("evidence_quality"), "evidence_quality")
        recency = _unit_interval(event.get("recency_factor"), "recency_factor")
        quality_values.append(quality)
        score_suppressed_reason = None
        corroborated = True
        if definition.requires_corroboration:
            corroborating_ids = event.get("corroborating_signal_ids", [])
            if not isinstance(corroborating_ids, list) or any(not isinstance(value, str) for value in corroborating_ids):
                raise ValueError("corroborating_signal_ids must be a list of signal IDs")
            corroborated = any(value in event_signal_ids and value != signal_id for value in corroborating_ids)
            if not corroborated:
                score_suppressed_reason = "requires_corroboration"
        if not definition.score_eligible:
            score_suppressed_reason = "context_only"
        score_eligible = definition.score_eligible and corroborated
        raw_contribution = definition.weight * quality * recency if score_eligible else 0.0
        family_totals[definition.family] += raw_contribution
        contributions.append({
            "signal_id": definition.signal_id,
            "signal_name": definition.name,
            "family": definition.family,
            "evidence_id": evidence_id,
            "source": event["source"].strip(),
            "observed_at": event["observed_at"].strip(),
            "base_weight": definition.weight,
            "evidence_quality": quality,
            "recency_factor": recency,
            "raw_contribution": round(raw_contribution, 4),
            "source_status": definition.source_status,
            "score_eligible": score_eligible,
            "score_suppressed_reason": score_suppressed_reason,
        })

    family_contributions = {
        family: round(min(total, FAMILY_CAPS[family]), 4)
        for family, total in sorted(family_totals.items())
    }
    score = round(min(100.0, sum(family_contributions.values())), 2)
    evidence_count = len(seen_evidence)
    independent_families = sum(1 for value in family_contributions.values() if value > 0)
    evidence_confidence = round(sum(quality_values) / len(quality_values), 4) if quality_values else 0.0

    if score >= 90:
        risk_level = "CRITICAL"
    elif score >= 75:
        risk_level = "HIGH"
    elif score >= 60:
        risk_level = "ELEVATED"
    elif score >= 40:
        risk_level = "MEDIUM"
    elif score >= 20:
        risk_level = "LOW"
    else:
        risk_level = "OBSERVE"

    threshold_met = score >= escalation_threshold
    enough_independent_support = (
        independent_families >= minimum_independent_families
        and evidence_count >= minimum_evidence_count
    )
    case_eligible = threshold_met and enough_independent_support
    if not threshold_met:
        case_block_reason = "threshold_not_met"
    elif not enough_independent_support:
        case_block_reason = "insufficient_independent_evidence"
    else:
        case_block_reason = None

    return {
        "score": score,
        "risk_level": risk_level,
        "evidence_confidence": evidence_confidence,
        "evidence_count": evidence_count,
        "independent_families": independent_families,
        "threshold": float(escalation_threshold),
        "threshold_met": threshold_met,
        "case_eligible": case_eligible,
        "case_block_reason": case_block_reason,
        "family_contributions": family_contributions,
        "contributions": contributions,
        "deduplicated_evidence_ids": deduplicated,
        "engine_version": "multi-signal-shadow-v1",
        "registry_version": REGISTRY_VERSION,
        "score_semantics": "priority_score_not_probability_or_guilt",
    }
