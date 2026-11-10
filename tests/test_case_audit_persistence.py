from finzanjir_ai.case.manager import CaseManager


def test_human_review_persists_decision_statuses_and_audit_event():
    manager = CaseManager()
    manager.open_case(
        case_id="case-audit-1",
        signal_ids=["sig-1"],
        risk_id="risk-1",
        threshold_id="thr-1",
        transaction_id="tx-1",
        escalation_met=True,
    )

    result = manager.apply_human_decision(
        case_id="case-audit-1",
        actor_id="reviewer-1",
        decision="APPROVE_ACTION",
        reason="Evidence supports continued review.",
    )

    assert manager.get_case("case-audit-1")["status"] == "ACTIONED"
    assert manager.get_human_decision("decision-case-audit-1") == result["human_decision"]
    assert manager.get_bank_status("case-audit-1") == result["bank_status"]
    assert manager.get_citizen_status("case-audit-1") == result["citizen_status"]
    assert manager.get_audit_event("audit-case-audit-1") == result["audit_event"]
