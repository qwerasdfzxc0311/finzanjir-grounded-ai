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



def test_rejected_human_decision_leaves_case_and_related_records_unchanged():
    manager = CaseManager()
    _open_case(manager)

    with pytest.raises(ValueError, match="Unsupported human decision"):
        manager.apply_human_decision(
            case_id="CASE-META-001",
            actor_id="reviewer",
            decision="BLOCK_ACCOUNT",
            reason="Unsupported action must not mutate the case.",
        )

    assert manager.get_case("CASE-META-001")["status"] == "OPEN"
    assert manager._human_decisions == {}
    assert manager._bank_statuses == {}
    assert manager._citizen_statuses == {}
    assert manager._audit_events == {}
