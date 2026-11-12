import pytest

from finzanjir_ai.case.manager import CaseManager


def _open_case(manager: CaseManager) -> None:
    manager.open_case(
        case_id="CASE-SYNTHETIC-STATUS-001",
        signal_ids=["signal-1"],
        risk_id="risk-1",
        threshold_id="threshold-1",
        transaction_id="TX-SYNTHETIC-STATUS-001",
        escalation_met=True,
    )


def test_non_authoritative_synthetic_decision_does_not_action_case():
    manager = CaseManager()
    _open_case(manager)

    result = manager.apply_human_decision(
        case_id="CASE-SYNTHETIC-STATUS-001",
        actor_id="demo-reviewer",
        decision="APPROVE_ACTION",
        reason="Synthetic demo evidence supports continued review.",
        decision_origin="synthetic_demo",
        actor_type="synthetic_demo",
        is_authoritative=False,
    )

    assert result["case"]["status"] == "OPEN"
    assert manager.get_case("CASE-SYNTHETIC-STATUS-001")["status"] == "OPEN"
    assert result["audit_event"]["change"]["case_status"] == "OPEN"


def test_non_authoritative_synthetic_decision_does_not_create_downstream_statuses():
    manager = CaseManager()
    _open_case(manager)

    result = manager.apply_human_decision(
        case_id="CASE-SYNTHETIC-STATUS-001",
        actor_id="demo-reviewer",
        decision="APPROVE_ACTION",
        reason="Synthetic demo evidence supports continued review.",
        decision_origin="synthetic_demo",
        actor_type="synthetic_demo",
        is_authoritative=False,
    )

    with pytest.raises(ValueError, match="Unknown bank status"):
        manager.get_bank_status("CASE-SYNTHETIC-STATUS-001")

    with pytest.raises(ValueError, match="Unknown citizen status"):
        manager.get_citizen_status("CASE-SYNTHETIC-STATUS-001")

    assert result["bank_status"] is None
    assert result["citizen_status"] is None
