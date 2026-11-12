from __future__ import annotations

from typing import Any

from .scoring import evaluate_signal_set


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
