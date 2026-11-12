import pytest

from finzanjir_ai.automation.policy import AutomationSafetyPolicy


def test_automation_policy_requires_allowed_action_and_explicit_reason():
    policy = AutomationSafetyPolicy(allowed_actions={"CREATE_CASE"})

    with pytest.raises(ValueError, match="not allowed"):
        policy.authorize(action="BLOCK_CARD", reason="high risk")

    with pytest.raises(ValueError, match="reason"):
        policy.authorize(action="CREATE_CASE", reason="")


def test_automation_policy_stops_safely_on_uncertain_or_timeout():
    policy = AutomationSafetyPolicy(allowed_actions={"CREATE_CASE"})

    assert policy.authorize(action="CREATE_CASE", reason="high risk", state="authorized")["status"] == "AUTHORIZED"
    assert policy.authorize(action="CREATE_CASE", reason="uncertain evidence", state="uncertain") == {
        "status": "SAFE_STOP",
        "route": "human_review",
    }
    assert policy.authorize(action="CREATE_CASE", reason="timeout", state="timeout") == {
        "status": "SAFE_STOP",
        "route": "human_review",
    }


def test_kill_switch_and_open_circuit_breaker_force_human_review():
    policy = AutomationSafetyPolicy(allowed_actions={"CREATE_CASE"})

    assert policy.authorize(
        action="CREATE_CASE", reason="approved", kill_switch_enabled=False
    ) == {
        "status": "SAFE_STOP",
        "route": "human_review",
        "reason": "kill_switch_disabled",
    }
    assert policy.authorize(
        action="CREATE_CASE", reason="approved", circuit_breaker_state="open"
    ) == {
        "status": "SAFE_STOP",
        "route": "human_review",
        "reason": "circuit_breaker_open",
    }


def test_circuit_breaker_trips_and_requires_distinct_manual_reset():
    import pytest
    from finzanjir_ai.automation.policy import AutomationCircuitBreaker

    breaker = AutomationCircuitBreaker(failure_threshold=2)
    assert breaker.record_failure(actor="monitor", reason="first timeout")["state"] == "closed"
    result = breaker.record_failure(actor="monitor", reason="second timeout")
    assert result == {"state": "open", "failure_count": 2, "tripped": True}
    assert breaker.record_success()["reset"] is False

    with pytest.raises(ValueError, match="distinct approver"):
        breaker.reset(approved_by="monitor", reason="attempted self reset")

    reset = breaker.reset(approved_by="security-reviewer", reason="recovery verified")
    assert reset == {"state": "closed", "failure_count": 0, "reset": True}
    assert breaker.history()[-1]["event"] == "manual_reset"


def test_circuit_breaker_rejects_invalid_threshold_and_gate_types():
    import pytest
    from finzanjir_ai.automation.policy import AutomationCircuitBreaker

    with pytest.raises(ValueError, match="positive integer"):
        AutomationCircuitBreaker(failure_threshold=True)
    with pytest.raises(ValueError, match="kill_switch_enabled"):
        AutomationSafetyPolicy(allowed_actions={"CREATE_CASE"}).authorize(
            action="CREATE_CASE", reason="approved", kill_switch_enabled="false"
        )


def test_automation_rejects_non_string_circuit_breaker_and_state():
    import pytest

    policy = AutomationSafetyPolicy(allowed_actions={"CREATE_CASE"})
    with pytest.raises(ValueError, match="circuit_breaker_state"):
        policy.authorize(
            action="CREATE_CASE", reason="approved", circuit_breaker_state=[]
        )
    with pytest.raises(ValueError, match="state must be a string"):
        policy.authorize(action="CREATE_CASE", reason="approved", state=[])
