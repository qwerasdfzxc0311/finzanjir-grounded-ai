import pytest

from finzanjir_ai.case.manager import CaseManager


def _open_case(manager: CaseManager) -> None:
    manager.open_case(
        case_id="CASE-META-001",
        signal_ids=["signal-1"],
        risk_id="risk-1",
        threshold_id="threshold-1",
        transaction_id="TX-META-001",
        escalation_met=True,
    )


def test_synthetic_demo_metadata_is_persisted_on_human_decision_and_audit():
    manager = CaseManager()
    _open_case(manager)

    result = manager.apply_human_decision(
        case_id="CASE-META-001",
        actor_id="demo-reviewer",
        decision="APPROVE_ACTION",
        reason="Synthetic demo evidence supports continued review.",
        decision_origin="synthetic_demo",
        actor_type="synthetic_demo",
        is_authoritative=False,
    )

    decision_id = result["human_decision"]["decision_id"]
    audit_id = result["audit_event"]["audit_id"]

    assert manager.get_human_decision(decision_id)["is_authoritative"] is False
    assert manager.get_human_decision(decision_id)["decision_origin"] == "synthetic_demo"
    assert manager.get_human_decision(decision_id)["actor_type"] == "synthetic_demo"

    audit = manager.get_audit_event(audit_id)
    assert audit["change"]["is_authoritative"] is False
    assert audit["change"]["decision_origin"] == "synthetic_demo"
    assert audit["change"]["actor_type"] == "synthetic_demo"


def test_synthetic_demo_cannot_be_marked_authoritative():
    manager = CaseManager()
    _open_case(manager)

    with pytest.raises(ValueError, match="synthetic_demo.*non-authoritative"):
        manager.apply_human_decision(
            case_id="CASE-META-001",
            actor_id="demo-reviewer",
            decision="APPROVE_ACTION",
            reason="Synthetic demo evidence supports continued review.",
            decision_origin="synthetic_demo",
            actor_type="synthetic_demo",
            is_authoritative=True,
        )
