from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class AuditLog:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def append(self, *, actor_id: str, event_type: str, object_type: str, object_id: str, details: dict[str, Any]) -> dict[str, Any]:
        event = {
            "audit_id": f"audit-{len(self._events) + 1:06d}",
            "actor_id": actor_id,
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "details": dict(details),
        }
        self._events.append(event)
        return dict(event)

    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)


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
        "average_review_seconds": review_seconds_total / cases_opened if cases_opened else 0.0,
    }
