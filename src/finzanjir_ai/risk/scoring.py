from __future__ import annotations

import math
from datetime import datetime
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
    """Score evidence-backed signals without treating the score as probability.

    Each event requires signal_id, evidence_id, source, observed_at,
    evidence_quality and recency_factor. Reused evidence IDs are grouped and
    only the strongest eligible contribution is counted. Corroboration must
    come from a different evidence ID.
    """
    if not isinstance(signal_events, list):
        raise ValueError("signal_events must be a list")
    if len(signal_events) > 100:
        raise ValueError("signal_events cannot contain more than 100 items")
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

    normalized: list[dict[str, Any]] = []
    evidence_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_event_keys: dict[str, str] = {}

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
        try:
            observed_at = datetime.fromisoformat(event["observed_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"signal_events[{index}].observed_at must be ISO-8601") from exc
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError(f"signal_events[{index}].observed_at must include a timezone")
        event_key = event.get("event_key", event["evidence_id"].strip())
        if not isinstance(event_key, str) or not event_key.strip():
            raise ValueError(f"signal_events[{index}].event_key must be a non-empty string")
        event_key = event_key.strip()
        evidence_id = event["evidence_id"].strip()
        prior_event_key = evidence_event_keys.get(evidence_id)
        if prior_event_key is not None and prior_event_key != event_key:
            raise ValueError("the same evidence_id cannot refer to multiple event_key values")
        evidence_event_keys[evidence_id] = event_key
        corroborating_ids = event.get("corroborating_signal_ids", [])
        if (
            not isinstance(corroborating_ids, list)
            or any(not isinstance(value, str) or value not in SIGNAL_REGISTRY for value in corroborating_ids)
            or len(corroborating_ids) != len(set(corroborating_ids))
        ):
            raise ValueError("corroborating_signal_ids must contain unique registered signal IDs")
        rule_version = event.get("rule_version", "unspecified")
        detector_version = event.get("detector_version", "unspecified")
        if not isinstance(rule_version, str) or not rule_version.strip():
            raise ValueError("rule_version must be a non-empty string")
        if not isinstance(detector_version, str) or not detector_version.strip():
            raise ValueError("detector_version must be a non-empty string")
        item = {
            "definition": definition,
            "signal_id": signal_id,
            "evidence_id": evidence_id,
            "event_key": event_key,
            "source": event["source"].strip(),
            "observed_at": event["observed_at"].strip(),
            "evidence_quality": _unit_interval(event.get("evidence_quality"), "evidence_quality"),
            "recency_factor": _unit_interval(event.get("recency_factor"), "recency_factor"),
            "corroborating_signal_ids": set(corroborating_ids),
            "rule_version": rule_version.strip(),
            "detector_version": detector_version.strip(),
        }
        normalized.append(item)
        evidence_groups[item["event_key"]].append(item)

    signal_ids_by_event = {
        event_key: {item["signal_id"] for item in items}
        for event_key, items in evidence_groups.items()
    }
    contributions: list[dict[str, Any]] = []
    deduplicated: list[str] = []
    deduplicated_event_keys: list[str] = []
    family_totals: dict[str, float] = defaultdict(float)
    quality_values: list[float] = []

    for event_key in sorted(evidence_groups):
        options: list[tuple[float, str, dict[str, Any], str | None]] = []
        for item in evidence_groups[event_key]:
            definition = item["definition"]
            corroborated = any(
                signal_id in other_signal_ids
                for other_event_key, other_signal_ids in signal_ids_by_event.items()
                if other_event_key != event_key
                for signal_id in item["corroborating_signal_ids"]
            )
            suppressed_reason = None
            if not definition.score_eligible:
                suppressed_reason = "context_only"
            elif definition.requires_corroboration and not corroborated:
                suppressed_reason = "requires_corroboration"
            eligible = suppressed_reason is None
            raw = definition.weight * item["evidence_quality"] * item["recency_factor"] if eligible else 0.0
            options.append((raw, definition.signal_id, item, suppressed_reason))

        # Stable, order-independent deduplication: highest eligible contribution wins;
        # signal ID breaks ties deterministically.
        raw_contribution, _, chosen, suppressed_reason = sorted(
            options, key=lambda option: (-option[0], option[1])
        )[0]
        definition = chosen["definition"]
        quality_values.append(chosen["evidence_quality"])
        family_totals[definition.family] += raw_contribution
        if len(options) > 1:
            deduplicated.extend(sorted({item["evidence_id"] for item in evidence_groups[event_key]}))
            deduplicated_event_keys.append(event_key)
        contributions.append({
            "signal_id": definition.signal_id,
            "signal_name": definition.name,
            "family": definition.family,
            "evidence_id": chosen["evidence_id"],
            "event_key": event_key,
            "source": chosen["source"],
            "observed_at": chosen["observed_at"],
            "rule_version": chosen["rule_version"],
            "detector_version": chosen["detector_version"],
            "base_weight": definition.weight,
            "evidence_quality": chosen["evidence_quality"],
            "recency_factor": chosen["recency_factor"],
            "raw_contribution": round(raw_contribution, 4),
            "source_status": definition.source_status,
            "score_eligible": suppressed_reason is None,
            "score_suppressed_reason": suppressed_reason,
        })

    family_contributions = {
        family: round(min(total, FAMILY_CAPS[family]), 4)
        for family, total in sorted(family_totals.items())
    }
    score = round(min(100.0, sum(family_contributions.values())), 2)
    evidence_count = len(evidence_groups)
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
        "deduplicated_evidence_ids": sorted(set(deduplicated)),
        "deduplicated_event_keys": deduplicated_event_keys,
        "engine_version": "multi-signal-shadow-v1",
        "registry_version": REGISTRY_VERSION,
        "score_semantics": "priority_score_not_probability_or_guilt",
    }
