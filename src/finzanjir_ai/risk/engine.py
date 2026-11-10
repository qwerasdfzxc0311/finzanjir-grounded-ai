from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskEvaluation:
    signal_score: float
    evidence_count: int
    risk_level: str
    threshold_met: bool
    case_should_open: bool


def evaluate_risk(*, signal_score: float, evidence_count: int, escalation_threshold: float) -> RiskEvaluation:
    if not 0 <= signal_score <= 1:
        raise ValueError("signal_score must be between 0 and 1")
    if evidence_count < 0:
        raise ValueError("evidence_count must be non-negative")
    if not 0 <= escalation_threshold <= 1:
        raise ValueError("escalation_threshold must be between 0 and 1")

    if signal_score >= 0.8:
        risk_level = "HIGH"
    elif signal_score >= 0.5:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    threshold_met = signal_score >= escalation_threshold and evidence_count > 0
    return RiskEvaluation(
        signal_score=signal_score,
        evidence_count=evidence_count,
        risk_level=risk_level,
        threshold_met=threshold_met,
        case_should_open=threshold_met,
    )
