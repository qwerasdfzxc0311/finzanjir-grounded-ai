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
