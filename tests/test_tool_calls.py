import json

import pytest

from finzanjir_ai.training.tool_calls import validate_tool_call


def envelope(**overrides):
    payload = {
        "version": 1,
        "call_id": "call_01",
        "tool": "lookup.project_docs",
        "arguments": {"query": "FINZANJIR maqsadi", "limit": 5},
        "data_classification": "project_internal",
        "approval_required": True,
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_valid_envelope_is_parsed_but_not_executed():
    request = validate_tool_call(
        envelope(),
        allowed_tools={"lookup.project_docs"},
    )
    assert request.call_id == "call_01"
    assert request.tool == "lookup.project_docs"
    assert request.arguments["limit"] == 5
    assert request.approval_required is True


def test_empty_allowlist_and_unknown_tool_are_denied():
    with pytest.raises(ValueError, match="allowlisted"):
        validate_tool_call(envelope())
    with pytest.raises(ValueError, match="allowlisted"):
        validate_tool_call(envelope(), allowed_tools={"search.web"})


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"approval_required": False}, "explicit approval"),
        ({"data_classification": "sensitive"}, "classification"),
        ({"data_classification": "restricted"}, "classification"),
        ({"tool": "Bad Tool"}, "tool name"),
        ({"call_id": "bad id"}, "call_id"),
        ({"version": 2}, "version"),
        ({"arguments": []}, "JSON object"),
        ({"extra": "field"}, "missing or unknown"),
    ],
)
def test_invalid_envelopes_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        validate_tool_call(
            envelope(**overrides),
            allowed_tools={"lookup.project_docs", "Bad Tool"},
        )


def test_duplicate_json_keys_are_rejected():
    raw = (
        '{"version":1,"call_id":"a","tool":"lookup.project_docs",'
        '"arguments":{},"arguments":{"x":1},'
        '"data_classification":"public","approval_required":true}'
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_tool_call(raw, allowed_tools={"lookup.project_docs"})


def test_oversized_and_deep_arguments_are_rejected():
    with pytest.raises(ValueError, match="maximum size"):
        validate_tool_call(" " * 16385, allowed_tools={"lookup.project_docs"})
    deep = {"x": {"x": {"x": {"x": {"x": {"x": {"x": {"x": {"x": 1}}}}}}}}}
    with pytest.raises(ValueError, match="nesting"):
        validate_tool_call(
            envelope(arguments=deep),
            allowed_tools={"lookup.project_docs"},
        )


def test_non_finite_json_numbers_are_rejected():
    with pytest.raises(ValueError, match="non-finite"):
        validate_tool_call(
            envelope(arguments={"amount": float("nan")}),
            allowed_tools={"lookup.project_docs"},
        )
