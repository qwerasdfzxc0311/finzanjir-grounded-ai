from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("contracts/event_contracts_v1.json")


def _load_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_nonempty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")


def _validate_timestamp(value: Any, field: str) -> None:
    _require_nonempty_string(value, field)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc


def validate_object(object_type: str, payload: dict[str, Any]) -> None:
    contract = _load_contract()
    schemas = contract["schemas"]
    if object_type not in schemas:
        raise ValueError(f"Unknown object type: {object_type}")
    if not isinstance(payload, dict):
        raise ValueError("object payload must be an object")

    missing = [field for field in schemas[object_type]["required"] if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")

    _require_nonempty_string(payload["id"], "id")

    lifecycle = contract.get("lifecycle", {}).get(object_type)
    if lifecycle and "status" in payload and payload["status"] not in lifecycle:
        raise ValueError(f"Invalid status for {object_type}: {payload['status']}")


def validate_event_envelope(envelope: dict[str, Any]) -> None:
    contract = _load_contract()
    required = contract["event_envelope"]["required"]
    missing = [field for field in required if field not in envelope]
    if missing:
        raise ValueError(f"Missing event envelope fields: {sorted(missing)}")

    for field in ("event_id", "event_type", "actor_id", "scope", "object_type", "object_id"):
        _require_nonempty_string(envelope[field], field)
    _validate_timestamp(envelope["occurred_at"], "occurred_at")

    scopes = contract["event_envelope"]["scopes"]
    if envelope["scope"] not in scopes:
        raise ValueError(f"Invalid scope: {envelope['scope']}")

    if not isinstance(envelope["payload"], dict):
        raise ValueError("payload must be an object")

    validate_object(envelope["object_type"], envelope["payload"])

    if envelope["scope"] == "cross_bank":
        if not contract["event_envelope"]["cross_bank_requires_explicit_scope"]:
            raise ValueError("cross-bank events require explicit scope")


def build_event_envelope(
    *,
    event_id: str,
    event_type: str,
    occurred_at: str,
    actor_id: str,
    scope: str,
    object_type: str,
    object_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "actor_id": actor_id,
        "scope": scope,
        "object_type": object_type,
        "object_id": object_id,
        "payload": payload,
    }
    validate_event_envelope(envelope)
    return envelope
