from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class AuditLog:
    ALLOWED_SCOPES = frozenset({"bank_internal", "cross_bank"})
    ALLOWED_DATA_MODES = frozenset({"synthetic", "real", "unknown"})

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def append(
        self,
        *,
        actor_id: str,
        event_type: str,
        object_type: str,
        object_id: str,
        details: dict[str, Any],
        source: str = "finzanjir-prototype",
        scope: str = "bank_internal",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        data_mode: str = "synthetic",
    ) -> dict[str, Any]:
        for field, value in (
            ("actor_id", actor_id),
            ("event_type", event_type),
            ("object_type", object_type),
            ("object_id", object_id),
            ("source", source),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if scope not in self.ALLOWED_SCOPES:
            raise ValueError("scope must be bank_internal or cross_bank")
        if data_mode not in self.ALLOWED_DATA_MODES:
            raise ValueError("data_mode must be synthetic, real, or unknown")
        if correlation_id is None:
            correlation_id = object_id
        if not isinstance(correlation_id, str) or not correlation_id.strip():
            raise ValueError("correlation_id must be a non-empty string")
        if causation_id is not None and (not isinstance(causation_id, str) or not causation_id.strip()):
            raise ValueError("causation_id must be a non-empty string or None")
        if not isinstance(details, dict):
            raise ValueError("details must be an object")

        event_id = f"audit-{uuid4().hex}"
        occurred_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = dict(details)
        event = {
            # Canonical event-envelope v2 fields.
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "actor_id": actor_id.strip(),
            "source": source.strip(),
            "scope": scope,
            "object_type": object_type.strip(),
            "object_id": object_id.strip(),
            "correlation_id": correlation_id.strip(),
            "causation_id": causation_id.strip() if causation_id else None,
            "payload": payload,
            "data_mode": data_mode,
            "schema_version": "event-envelope-v2",
            # Legacy aliases retained for v1 consumers.
            "audit_id": event_id,
            "details": payload,
        }
        self._events.append(deepcopy(event))
        return deepcopy(event)

    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)


def calculate_kpis(*, signals_detected: int, cases_opened: int, cases_actioned: int, review_seconds_total: int, data_mode: str) -> dict[str, Any]:
    if min(signals_detected, cases_opened, cases_actioned, review_seconds_total) < 0:
        raise ValueError("KPI inputs must be non-negative")
    if cases_opened > signals_detected:
        raise ValueError("cases_opened cannot exceed signals_detected")
    if cases_actioned > cases_opened:
        raise ValueError("cases_actioned cannot exceed cases_opened")
    return {
        "data_mode": data_mode,
        "signal_to_case_rate": cases_opened / signals_detected if signals_detected else 0.0,
        "case_action_rate": cases_actioned / cases_opened if cases_opened else 0.0,
        "average_review_seconds": review_seconds_total / cases_actioned if cases_actioned else 0.0,
    }
