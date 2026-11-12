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


def test_threshold_update_versions_config_and_emits_audit_event():
    manager = ThresholdManager()
    result = manager.update_threshold(
        value=82,
        changed_by="reviewer-test",
        reason="Synthetic calibration exercise",
        expected_version=1,
    )

    active = manager.get_active()
    history = manager.get_history()

    assert active["value"] == 82
    assert active["version"] == 2
    assert history[0]["status"] == "SUPERSEDED"
    assert history[1]["status"] == "ACTIVE"
    assert result["threshold"] == active
    assert result["audit_event"]["event_type"] == "THRESHOLD_UPDATED"
    assert result["audit_event"]["payload"]["previous_value"] == 75
    assert result["audit_event"]["payload"]["new_value"] == 82
    assert result["audit_event"]["payload"]["new_version"] == 2
    assert result["audit_event"]["data_mode"] == "synthetic"


def test_threshold_manager_rejects_stale_version_and_invalid_updates():
    manager = ThresholdManager()
    manager.update_threshold(
        value=80,
        changed_by="reviewer-test",
        reason="First update",
        expected_version=1,
    )

    with pytest.raises(ValueError, match="version conflict"):
        manager.update_threshold(
            value=85,
            changed_by="reviewer-test",
            reason="Stale update",
            expected_version=1,
        )
    with pytest.raises(ValueError, match="between 0 and 100"):
        manager.update_threshold(
            value=101,
            changed_by="reviewer-test",
            reason="Invalid range",
            expected_version=2,
        )
    with pytest.raises(ValueError, match="must differ"):
        manager.update_threshold(
            value=80,
            changed_by="reviewer-test",
            reason="No-op update",
            expected_version=2,
        )


def test_threshold_history_is_returned_as_detached_copies():
    manager = ThresholdManager()
    history = manager.get_history()
    history[0]["value"] = 1

    assert manager.get_active()["value"] == 75
