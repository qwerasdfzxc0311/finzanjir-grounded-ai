from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataDisclosurePolicy:
    """Fail-closed controls for external data disclosure."""

    allowed_recipients: frozenset[str]
    allowed_fields: frozenset[str]

    def __init__(self, *, allowed_recipients: set[str] | frozenset[str], allowed_fields: set[str] | frozenset[str]) -> None:
        recipients = frozenset(value.strip() for value in allowed_recipients if isinstance(value, str) and value.strip())
        fields = frozenset(value.strip() for value in allowed_fields if isinstance(value, str) and value.strip())
        if not recipients:
            raise ValueError("at least one allowed recipient is required")
        if not fields:
            raise ValueError("at least one allowed field is required")
        object.__setattr__(self, "allowed_recipients", recipients)
        object.__setattr__(self, "allowed_fields", fields)

    def prepare_transfer(
        self,
        *,
        purpose: str,
        recipient: str,
        requested_fields: list[str],
        permission: bool,
    ) -> dict[str, Any]:
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError("sharing purpose is required")
        if not isinstance(permission, bool):
            raise ValueError("sharing permission must be boolean")
        if not permission:
            raise ValueError("sharing permission is required")
        if not isinstance(recipient, str) or recipient.strip() not in self.allowed_recipients:
            raise ValueError("recipient is not authorized")
        if not requested_fields or any(not isinstance(value, str) or not value.strip() for value in requested_fields):
            raise ValueError("requested fields are required")

        normalized_fields = [value.strip() for value in requested_fields]
        if len(set(normalized_fields)) != len(normalized_fields):
            raise ValueError("requested fields must be unique")
        if any(value not in self.allowed_fields for value in normalized_fields):
            raise ValueError("requested fields exceed the minimal disclosure set")

        audit = {
            "event_type": "DataDisclosurePrepared",
            "purpose": purpose.strip(),
            "recipient": recipient.strip(),
            "permission": permission,
            "requested_fields": list(normalized_fields),
            "disclosed_fields": list(normalized_fields),
        }
        return {
            "purpose": purpose.strip(),
            "recipient": recipient.strip(),
            "payload_fields": list(normalized_fields),
            "audit": audit,
        }
