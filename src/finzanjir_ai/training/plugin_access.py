from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class PluginAccessDecision:
    allowed: bool
    requires_confirmation: bool
    reason: str


def evaluate_plugin_access(
    capability_snapshot: Mapping[str, Any],
    *,
    plugin_id: str,
    action_id: str,
    required_scopes: Iterable[str] = (),
    data_classification: str = "public",
    user_approved: bool = False,
) -> PluginAccessDecision:
    """Evaluate host-reported plugin permissions; never discovers or executes plugins.

    capability_snapshot must be supplied by a trusted host integration, not by
    model output, user text, plugin output, or an untrusted project document.
    """
    if not isinstance(capability_snapshot, Mapping):
        return PluginAccessDecision(False, False, "host capability snapshot is unavailable")
    plugins = capability_snapshot.get("plugins")
    if not isinstance(plugins, Mapping):
        return PluginAccessDecision(False, False, "host did not provide a plugin inventory")
    plugin = plugins.get(plugin_id)
    if not isinstance(plugin, Mapping):
        return PluginAccessDecision(False, False, "plugin is not present in host inventory")
    if plugin.get("connected") is not True:
        return PluginAccessDecision(False, False, "plugin is not connected")
    if plugin.get("enabled") is not True:
        return PluginAccessDecision(False, False, "plugin is not enabled")
    actions = plugin.get("actions")
    if not isinstance(actions, Mapping):
        return PluginAccessDecision(False, False, "plugin action permissions are unavailable")
    action = actions.get(action_id)
    if not isinstance(action, Mapping):
        return PluginAccessDecision(False, False, "action is not exposed by this plugin")
    if action.get("enabled") is not True:
        return PluginAccessDecision(False, False, "action is not enabled")

    granted = plugin.get("granted_scopes")
    if not isinstance(granted, (list, tuple, set, frozenset)) or any(
        not isinstance(scope, str) or not scope.strip() for scope in granted
    ):
        return PluginAccessDecision(False, False, "granted scopes are not verifiable")

    if isinstance(required_scopes, (str, bytes)):
        return PluginAccessDecision(False, False, "caller required scopes are invalid")
    try:
        requested_scopes = tuple(required_scopes)
    except TypeError:
        return PluginAccessDecision(False, False, "caller required scopes are invalid")
    if any(not isinstance(scope, str) or not scope.strip() for scope in requested_scopes):
        return PluginAccessDecision(False, False, "caller required scopes are invalid")

    needed = frozenset(requested_scopes)
    granted_set = frozenset(granted)
    if not needed.issubset(granted_set):
        return PluginAccessDecision(False, False, "required permission scopes are not granted")
    if data_classification not in {"public", "project_internal"}:
        return PluginAccessDecision(False, False, "data classification requires a separate privacy and legal gate")

    # A missing declaration is not equivalent to an explicit no-scope action.
    if "required_scopes" not in action:
        return PluginAccessDecision(False, False, "action scope declaration is missing")
    action_scopes = action["required_scopes"]
    if not isinstance(action_scopes, (list, tuple)) or any(
        not isinstance(scope, str) or not scope.strip() for scope in action_scopes
    ):
        return PluginAccessDecision(False, False, "action scope declaration is invalid")
    action_scope_set = frozenset(action_scopes)
    if not action_scope_set.issubset(granted_set):
        return PluginAccessDecision(False, False, "plugin has not granted all action scopes")
    if not needed.issubset(action_scope_set):
        return PluginAccessDecision(False, False, "caller requested scopes do not match the declared action")

    risk = action.get("risk")
    if risk not in {"read_only", "write", "external_effect"}:
        return PluginAccessDecision(False, False, "action risk is unknown")
    preapproved = action.get("preapproved") is True
    if risk == "read_only" and preapproved:
        return PluginAccessDecision(True, False, "connected, enabled, scoped read-only action is preapproved")
    if user_approved is not True:
        return PluginAccessDecision(False, True, "explicit user confirmation is required for this action")
    return PluginAccessDecision(True, False, "action permissions verified and user confirmation supplied")
