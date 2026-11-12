from __future__ import annotations

from typing import Any

from .scoring import evaluate_signal_set
from .detectors import synthetic_signal_detector
from .registry import SIGNAL_REGISTRY


ALLOWED_LABELS = frozenset({"suspicious", "benign"})


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate_shadow_batch(
    scenarios: list[dict[str, Any]],
    *,
    escalation_threshold: float = 75,
) -> dict[str, Any]:
    """Evaluate labelled synthetic scenarios without creating Cases or actions.

    The output measures scoring/threshold behavior for supplied signal events.
    It does not measure the ability of upstream detectors to discover fraud
    from raw bank data and must not be presented as production performance.
    """
    if not isinstance(scenarios, list):
        raise ValueError("scenarios must be a list")
    if len(scenarios) > 500:
        raise ValueError("scenarios cannot contain more than 500 items")

    seen_ids: set[str] = set()
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    results: list[dict[str, Any]] = []

    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"scenarios[{index}] must be an object")
        scenario_id = scenario.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError(f"scenarios[{index}].scenario_id must be a non-empty string")
        scenario_id = scenario_id.strip()
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        seen_ids.add(scenario_id)

        expected = scenario.get("expected_label")
        if expected not in ALLOWED_LABELS:
            raise ValueError(f"scenarios[{index}].expected_label must be suspicious or benign")
        signal_events = scenario.get("signal_events")
        evaluation = evaluate_signal_set(
            signal_events,
            escalation_threshold=escalation_threshold,
        )
        predicted = "suspicious" if evaluation["case_eligible"] else "benign"

        if expected == "suspicious" and predicted == "suspicious":
            counts["tp"] += 1
        elif expected == "benign" and predicted == "suspicious":
            counts["fp"] += 1
        elif expected == "benign" and predicted == "benign":
            counts["tn"] += 1
        else:
            counts["fn"] += 1

        results.append({
            "scenario_id": scenario_id,
            "expected_label": expected,
            "predicted_label": predicted,
            "score": evaluation["score"],
            "risk_level": evaluation["risk_level"],
            "evidence_count": evaluation["evidence_count"],
            "independent_families": evaluation["independent_families"],
            "threshold_met": evaluation["threshold_met"],
            "case_eligible": evaluation["case_eligible"],
            "case_block_reason": evaluation["case_block_reason"],
            "registry_version": evaluation["registry_version"],
        })

    total = len(results)
    predicted_positive = counts["tp"] + counts["fp"]
    actual_positive = counts["tp"] + counts["fn"]
    actual_negative = counts["tn"] + counts["fp"]
    return {
        "data_mode": "synthetic",
        "evaluation_mode": "shadow_metrics_only",
        "scenario_count": total,
        "threshold": float(escalation_threshold),
        "confusion_matrix": counts,
        "metrics": {
            "precision": _ratio(counts["tp"], predicted_positive),
            "recall": _ratio(counts["tp"], actual_positive),
            "specificity": _ratio(counts["tn"], actual_negative),
            "false_positive_rate": _ratio(counts["fp"], actual_negative),
            "false_negative_rate": _ratio(counts["fn"], actual_positive),
            "accuracy": _ratio(counts["tp"] + counts["tn"], total),
            "referral_rate": _ratio(predicted_positive, total),
        },
        "results": results,
        "limitations": [
            "Only synthetic labels and supplied signal_events were evaluated.",
            "This does not measure raw-data detector recall or real-world fraud detection performance.",
            "Risk Score is a prioritization score, not a probability or guilt finding.",
            "No Case, payment, bank status, customer block, or authoritative decision is created.",
        ],
    }


def evaluate_detector_shadow_batch(
    scenarios: list[dict[str, Any]],
    *,
    escalation_threshold: float = 75,
) -> dict[str, Any]:
    """Evaluate source-feature detector + multi-signal scoring using synthetic scenarios.

    Scenarios declare target_signal_ids so missing target features are counted as
    abstentions, never silently treated as benign. No Cases or external actions
    are created.
    """
    if not isinstance(scenarios, list):
        raise ValueError("scenarios must be a list")
    if not 1 <= len(scenarios) <= 500:
        raise ValueError("scenarios must contain between 1 and 500 items")
    if not isinstance(escalation_threshold, (int, float)) or isinstance(escalation_threshold, bool) or not math.isfinite(escalation_threshold):
        raise ValueError("escalation_threshold must be finite")
    if not 0 <= escalation_threshold <= 100:
        raise ValueError("escalation_threshold must be between 0 and 100")

    detector = synthetic_signal_detector()
    seen_ids: set[str] = set()
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    abstained = {"suspicious": 0, "benign": 0}
    results: list[dict[str, Any]] = []

    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"scenarios[{index}] must be an object")
        scenario_id = scenario.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError(f"scenarios[{index}].scenario_id must be non-empty")
        scenario_id = scenario_id.strip()
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        seen_ids.add(scenario_id)

        if scenario.get("synthetic") is not True:
            raise ValueError("detector shadow evaluation accepts only explicitly synthetic scenarios")
        expected = scenario.get("expected_label")
        if expected not in ALLOWED_LABELS:
            raise ValueError(f"scenarios[{index}].expected_label must be suspicious or benign")
        target_ids = scenario.get("target_signal_ids")
        if (
            not isinstance(target_ids, list)
            or not target_ids
            or any(not isinstance(value, str) or value not in SIGNAL_REGISTRY for value in target_ids)
            or len(target_ids) != len(set(target_ids))
        ):
            raise ValueError("target_signal_ids must contain unique registered signal IDs")
        features = scenario.get("features")
        if not isinstance(features, dict):
            raise ValueError(f"scenarios[{index}].features must be an object")

        detection = detector.evaluate(
            scenario_id=scenario_id,
            observed_at=scenario.get("observed_at"),
            features=features,
            evidence_quality=scenario.get("evidence_quality", 1.0),
            recency_factor=scenario.get("recency_factor", 1.0),
        )
        by_id = {item["signal_id"]: item for item in detection["detections"]}
        target_results = [by_id[signal_id] for signal_id in target_ids]
        insufficient = [item["signal_id"] for item in target_results if item["status"] == "INSUFFICIENT_DATA"]
        evaluation = evaluate_signal_set(
            detection["signal_observations"],
            escalation_threshold=escalation_threshold,
        )
        if insufficient:
            predicted = "abstained_insufficient_data"
            abstained[expected] += 1
        else:
            predicted = "suspicious" if evaluation["case_eligible"] else "benign"
            if expected == "suspicious" and predicted == "suspicious":
                counts["tp"] += 1
            elif expected == "benign" and predicted == "suspicious":
                counts["fp"] += 1
            elif expected == "benign" and predicted == "benign":
                counts["tn"] += 1
            else:
                counts["fn"] += 1

        results.append({
            "scenario_id": scenario_id,
            "expected_label": expected,
            "predicted_label": predicted,
            "target_signal_ids": target_ids,
            "target_signal_statuses": {item["signal_id"]: item["status"] for item in target_results},
            "insufficient_target_signal_ids": insufficient,
            "detected_signal_ids": detection["detected_signal_ids"],
            "score": evaluation["score"],
            "risk_level": evaluation["risk_level"],
            "evidence_count": evaluation["evidence_count"],
            "independent_families": evaluation["independent_families"],
            "case_eligible": evaluation["case_eligible"],
            "case_block_reason": evaluation["case_block_reason"],
        })

    decisive = sum(counts.values())
    total = len(results)
    predicted_positive = counts["tp"] + counts["fp"]
    actual_positive = counts["tp"] + counts["fn"]
    actual_negative = counts["tn"] + counts["fp"]
    return {
        "data_mode": "synthetic",
        "evaluation_mode": "detector_and_scoring_shadow_metrics_only",
        "scenario_count": total,
        "decisive_scenario_count": decisive,
        "abstained_count": sum(abstained.values()),
        "abstained_by_expected_label": abstained,
        "coverage": _ratio(decisive, total),
        "abstention_rate": _ratio(sum(abstained.values()), total),
        "threshold": float(escalation_threshold),
        "confusion_matrix": counts,
        "metrics": {
            "precision": _ratio(counts["tp"], predicted_positive),
            "recall": _ratio(counts["tp"], actual_positive),
            "specificity": _ratio(counts["tn"], actual_negative),
            "false_positive_rate": _ratio(counts["fp"], actual_negative),
            "false_negative_rate": _ratio(counts["fn"], actual_positive),
            "accuracy": _ratio(counts["tp"] + counts["tn"], decisive),
            "referral_rate": _ratio(predicted_positive, decisive),
        },
        "results": results,
        "limitations": [
            "Only explicitly labelled synthetic feature bundles and candidate detector rules were evaluated.",
            "Target features that are missing are reported as abstentions, not benign outcomes.",
            "This does not measure real bank source coverage, real-world fraud prevalence, or production precision/recall.",
            "Risk Score is a prioritization score, not a probability or guilt finding.",
            "No Case, payment, bank status, customer block, or authoritative decision is created.",
        ],
    }
