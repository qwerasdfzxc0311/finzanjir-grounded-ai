import pytest

from finzanjir_ai.training.plugin_access import evaluate_plugin_access


def snapshot(**overrides):
    plugin = {
        "connected": True,
        "enabled": True,
        "granted_scopes": ["files.read"],
        "actions": {
            "search_files": {
                "enabled": True,
                "required_scopes": ["files.read"],
                "risk": "read_only",
                "preapproved": True,
            },
            "write_file": {
                "enabled": True,
                "required_scopes": ["files.write"],
                "risk": "write",
                "preapproved": False,
            },
        },
    }
    plugin.update(overrides)
    return {"plugins": {"drive": plugin}}


def test_preapproved_read_only_action_can_proceed():
    result = evaluate_plugin_access(
        snapshot(),
        plugin_id="drive",
        action_id="search_files",
        required_scopes=["files.read"],
    )
    assert result.allowed is True
    assert result.requires_confirmation is False


def test_unconnected_plugin_is_denied():
    result = evaluate_plugin_access(
        {"plugins": {"drive": {"connected": False}}},
        plugin_id="drive",
        action_id="search_files",
    )
    assert result.allowed is False
    assert "not connected" in result.reason


def test_missing_action_or_scope_is_denied():
    missing = evaluate_plugin_access(
        snapshot(),
        plugin_id="drive",
        action_id="delete_everything",
    )
    assert missing.allowed is False

    no_scope = evaluate_plugin_access(
        snapshot(),
        plugin_id="drive",
        action_id="search_files",
        required_scopes=["files.write"],
    )
    assert no_scope.allowed is False


def test_write_action_requires_explicit_user_approval():
    denied = evaluate_plugin_access(
        snapshot(granted_scopes=["files.read", "files.write"]),
        plugin_id="drive",
        action_id="write_file",
        required_scopes=["files.write"],
    )
    assert denied.allowed is False
    assert denied.requires_confirmation is True

    approved = evaluate_plugin_access(
        snapshot(granted_scopes=["files.read", "files.write"]),
        plugin_id="drive",
        action_id="write_file",
        required_scopes=["files.write"],
        user_approved=True,
    )
    assert approved.allowed is True


@pytest.mark.parametrize("classification", ["personal", "bank", "customer", "restricted"])
def test_sensitive_data_classes_are_denied(classification):
    result = evaluate_plugin_access(
        snapshot(),
        plugin_id="drive",
        action_id="search_files",
        data_classification=classification,
    )
    assert result.allowed is False


def test_unknown_risk_or_untrusted_snapshot_is_denied():
    result = evaluate_plugin_access(
        snapshot(actions={"search_files": {"enabled": True, "required_scopes": [], "risk": "unknown"}}),
        plugin_id="drive",
        action_id="search_files",
    )
    assert result.allowed is False
    assert evaluate_plugin_access(
        {},
        plugin_id="drive",
        action_id="search_files",
    ).allowed is False
