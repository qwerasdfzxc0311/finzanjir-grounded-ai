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
