from finzanjir_ai.case.manager import CaseManager


def test_case_is_opened_and_human_decision_updates_statuses():
    manager = CaseManager()
    case = manager.open_case(
        case_id="case-1",
        signal_ids=["sig-1"],
        risk_id="risk-1",
        threshold_id="thr-1",
        escalation_met=True,
    )
    assert case["status"] == "OPEN"

    result = manager.apply_human_decision(
        case_id="case-1",
        actor_id="reviewer-1",
        decision="APPROVE_ACTION",
        reason="Evidence supports continued review.",
    )
    assert result["case"]["status"] == "ACTIONED"
    assert result["bank_status"]["status"] == "REVIEW_REQUIRED"
    assert result["citizen_status"]["status"] == "UNDER_REVIEW"
    assert result["audit_event"]["object_type"] == "HumanDecision"


def test_case_cannot_open_without_escalation_threshold():
    manager = CaseManager()
    try:
        manager.open_case(
            case_id="case-2",
            signal_ids=["sig-2"],
            risk_id="risk-2",
            threshold_id="thr-2",
            escalation_met=False,
        )
    except ValueError:
        return
    raise AssertionError("Case must not open when escalation threshold is not met")
