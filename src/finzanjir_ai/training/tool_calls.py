from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable


_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_CALL_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_ALLOWED_CLASSIFICATIONS = frozenset({"public", "project_internal"})
_MAX_PAYLOAD_BYTES = 16_384
_MAX_DEPTH = 8
_MAX_NODES = 256


@dataclass(frozen=True)
class ToolCallRequest:
    """Validated request envelope only; this object never executes a tool."""

    call_id: str
    tool: str
    arguments: dict[str, Any]
    data_classification: str
    approval_required: bool = True


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _check_json_tree(value: Any, *, depth: int = 0, count: list[int] | None = None) -> None:
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > _MAX_NODES:
        raise ValueError("tool arguments contain too many values")
    if depth > _MAX_DEPTH:
        raise ValueError("tool arguments exceed maximum nesting depth")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("tool argument keys must be strings")
            _check_json_tree(child, depth=depth + 1, count=count)
    elif isinstance(value, list):
        for child in value:
            _check_json_tree(child, depth=depth + 1, count=count)
    elif isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("tool argument string is too long")
    elif value is None or isinstance(value, (bool, int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("non-finite numbers are not valid tool arguments")
    else:
        raise ValueError("tool arguments must contain JSON values only")


def validate_tool_call(
    serialized: str,
    *,
    allowed_tools: Iterable[str] = (),
) -> ToolCallRequest:
    """Validate a bounded, explicitly allowlisted tool-call envelope.

    Validation does not authorize execution. The caller must separately enforce
    user approval, tool-specific schemas, data permissions, and audit controls.
    """
    if not isinstance(serialized, str):
        raise TypeError("tool-call envelope must be JSON text")
    if len(serialized.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("tool-call envelope exceeds maximum size")
    try:
        payload = json.loads(serialized, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("tool-call envelope must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("tool-call envelope must be a JSON object")

    required = {"version", "call_id", "tool", "arguments", "data_classification", "approval_required"}
    if set(payload) != required:
        raise ValueError("tool-call envelope has missing or unknown fields")
    if payload["version"] != 1 or isinstance(payload["version"], bool):
        raise ValueError("unsupported tool-call envelope version")

    call_id = payload["call_id"]
    tool = payload["tool"]
    classification = payload["data_classification"]
    arguments = payload["arguments"]
    if not isinstance(call_id, str) or not _CALL_ID.fullmatch(call_id):
        raise ValueError("invalid tool call_id")
    if not isinstance(tool, str) or not _TOOL_NAME.fullmatch(tool):
        raise ValueError("invalid tool name")
    if tool not in frozenset(allowed_tools):
        raise ValueError("tool is not explicitly allowlisted")
    if not isinstance(classification, str) or classification not in _ALLOWED_CLASSIFICATIONS:
        raise ValueError("data classification is not permitted for tool calls")
    if payload["approval_required"] is not True:
        raise ValueError("tool calls must require explicit approval")
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be a JSON object")
    _check_json_tree(arguments)
    return ToolCallRequest(
        call_id=call_id,
        tool=tool,
        arguments=arguments,
        data_classification=classification,
        approval_required=True,
    )
