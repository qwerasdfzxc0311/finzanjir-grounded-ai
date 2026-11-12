import math

import pytest

from finzanjir_ai.risk.engine import evaluate_risk


def test_threshold_met_escalates_case():
    result = evaluate_risk(signal_score=0.82, evidence_count=2, escalation_threshold=0.75)
    assert result.risk_level == "HIGH"
    assert result.threshold_met is True
    assert result.case_should_open is True


def test_high_score_without_evidence_does_not_open_case():
    result = evaluate_risk(signal_score=0.95, evidence_count=0, escalation_threshold=0.75)
    assert result.threshold_met is False
    assert result.case_should_open is False


def test_threshold_not_met_does_not_open_case():
    result = evaluate_risk(signal_score=0.61, evidence_count=2, escalation_threshold=0.75)
    assert result.threshold_met is False
    assert result.case_should_open is False


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_risk_rejects_non_finite_signal_scores(value):
    with pytest.raises(ValueError, match="finite"):
        evaluate_risk(signal_score=value, evidence_count=1, escalation_threshold=0.75)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_risk_rejects_non_finite_escalation_thresholds(value):
    with pytest.raises(ValueError, match="finite"):
        evaluate_risk(signal_score=0.85, evidence_count=1, escalation_threshold=value)


def test_risk_rejects_non_integer_evidence_count():
    with pytest.raises(ValueError, match="integer"):
        evaluate_risk(signal_score=0.85, evidence_count=1.5, escalation_threshold=0.75)
