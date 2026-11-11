import json
from pathlib import Path

from finzanjir_ai.case.manager import CaseManager


def test_human_review_outputs_match_the_frozen_data_model_contract():
    contract = json.loads(Path("contracts/data_model_v1.json").read_text(encoding="utf-8"))
    manager = CaseManager()

    manager.open_case(
        case_id="case-contract-1",
        signal_ids=["sig-1"],
        risk_id="risk-1",
        threshold_id="thr-1",
        escalation_met=True,
    )
    result = manager.apply_human_decision(
        case_id="case-contract-1",
        actor_id="reviewer-1",
        decision="APPROVE_ACTION",
        reason="Evidence supports continued review.",
    )

    expected = contract["objects"]
    assert set(expected["Case"]["required"]).issubset(result["case"])
    assert set(expected["HumanDecision"]["required"]).issubset(result["human_decision"])
    assert set(expected["BankStatus"]["required"]).issubset(result["bank_status"])
    assert set(expected["CitizenStatus"]["required"]).issubset(result["citizen_status"])
    assert set(expected["AuditEvent"]["required"]).issubset(result["audit_event"])


def test_case_manager_rejects_threshold_bypass():
    manager = CaseManager()

    try:
        manager.open_case(
            case_id="case-threshold-bypass",
            signal_ids=["sig-1"],
            risk_id="risk-1",
            threshold_id="thr-1",
            escalation_met=False,
        )
    except ValueError as exc:
        assert "threshold" in str(exc)
    else:
        raise AssertionError("CaseManager must reject case creation below threshold")
