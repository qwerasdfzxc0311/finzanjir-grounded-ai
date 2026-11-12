import pytest

from finzanjir_ai.risk.thresholds import ThresholdManager


def test_threshold_manager_starts_with_one_active_version():
    manager = ThresholdManager()
    active = manager.get_active()

    assert active["id"] == "multi-signal-case-escalation"
    assert active["value"] == 75
    assert active["version"] == 1
    assert active["status"] == "ACTIVE"
    assert active["score_scale"] == "priority_0_100"
    assert active["data_mode"] == "synthetic"


def test_threshold_change_requires_proposal_and_distinct_approver():
    manager = ThresholdManager()
    proposed = manager.propose_threshold(
        value=82,
        proposed_by="analyst-test",
        reason="Synthetic calibration exercise",
        expected_version=1,
    )
    proposal_id = proposed["proposal"]["proposal_id"]

    with pytest.raises(ValueError, match="distinct approver"):
        manager.approve_proposal(proposal_id, approved_by="analyst-test")

    result = manager.approve_proposal(proposal_id, approved_by="reviewer-test")
    active = manager.get_active()
    history = manager.get_history()

    assert active["value"] == 82
    assert active["version"] == 2
    assert active["changed_by"] == "reviewer-test"
    assert history[0]["status"] == "SUPERSEDED"
    assert history[1]["status"] == "ACTIVE"
    assert result["proposal"]["status"] == "APPROVED"
    assert result["proposal"]["proposed_by"] == "analyst-test"
    assert result["proposal"]["approved_by"] == "reviewer-test"
    assert result["audit_event"]["event_type"] == "THRESHOLD_UPDATED"
    assert result["audit_event"]["payload"]["previous_value"] == 75
    assert result["audit_event"]["payload"]["new_value"] == 82
    assert result["audit_event"]["payload"]["proposal_id"] == proposal_id


def test_threshold_manager_rejects_stale_version_and_invalid_proposals():
    manager = ThresholdManager()
    with pytest.raises(ValueError, match="between 0 and 100"):
        manager.propose_threshold(
            value=101, proposed_by="analyst", reason="invalid", expected_version=1
        )
    with pytest.raises(ValueError, match="version conflict"):
        manager.propose_threshold(
            value=80, proposed_by="analyst", reason="stale", expected_version=2
        )

    proposal = manager.propose_threshold(
        value=80, proposed_by="analyst", reason="first", expected_version=1
    )["proposal"]
    manager.approve_proposal(proposal["proposal_id"], approved_by="reviewer")

    with pytest.raises(ValueError, match="must be re-created"):
        manager.approve_proposal(proposal["proposal_id"], approved_by="second-reviewer")
    with pytest.raises(ValueError, match="direct threshold updates are disabled"):
        manager.update_threshold(
            value=85, changed_by="analyst", reason="bypass", expected_version=2
        )


def test_threshold_proposal_can_be_rejected_only_by_a_distinct_reviewer():
    manager = ThresholdManager()
    proposal = manager.propose_threshold(
        value=80, proposed_by="analyst", reason="candidate", expected_version=1
    )["proposal"]

    with pytest.raises(ValueError, match="distinct reviewer"):
        manager.reject_proposal(
            proposal["proposal_id"], rejected_by="analyst", reason="reject"
        )

    rejected = manager.reject_proposal(
        proposal["proposal_id"], rejected_by="reviewer", reason="evidence insufficient"
    )
    assert rejected["proposal"]["status"] == "REJECTED"
    assert manager.get_active()["version"] == 1


def test_threshold_audit_failure_does_not_partially_activate_a_proposal(monkeypatch):
    manager = ThresholdManager()
    proposal = manager.propose_threshold(
        value=82, proposed_by="analyst", reason="synthetic proposal", expected_version=1
    )["proposal"]

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit unavailable")

    monkeypatch.setattr("finzanjir_ai.risk.thresholds.AuditLog.append", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        manager.approve_proposal(proposal["proposal_id"], approved_by="reviewer")

    assert manager.get_active()["version"] == 1
    assert manager.get_active()["value"] == 75
    assert manager.get_history()[0]["status"] == "ACTIVE"
    assert manager.get_proposals()[0]["status"] == "PENDING"


def test_threshold_history_and_proposals_are_returned_as_detached_copies():
    manager = ThresholdManager()
    proposal = manager.propose_threshold(
        value=80, proposed_by="analyst", reason="candidate", expected_version=1
    )["proposal"]
    history = manager.get_history()
    proposals = manager.get_proposals()
    history[0]["value"] = 1
    proposals[0]["status"] = "APPROVED"

    assert manager.get_active()["value"] == 75
    assert manager.get_proposals()[0]["status"] == "PENDING"
