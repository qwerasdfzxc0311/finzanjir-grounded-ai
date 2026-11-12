from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any

from finzanjir_ai.audit.service import AuditLog


class ThresholdManager:
    """In-memory, versioned threshold configuration for synthetic prototype flows."""

    def __init__(
        self,
        *,
        threshold_id: str = "multi-signal-case-escalation",
        default_value: float = 75,
    ) -> None:
        if not isinstance(threshold_id, str) or not threshold_id.strip():
            raise ValueError("threshold_id must be a non-empty string")
        self._validate_value(default_value)
        effective_at = self._now()
        self._history: list[dict[str, Any]] = [{
            "id": threshold_id.strip(),
            "type": "case_escalation",
            "value": float(default_value),
            "score_scale": "priority_0_100",
            "version": 1,
            "status": "ACTIVE",
            "effective_at": effective_at,
            "changed_by": "system:default",
            "reason": "Initial synthetic prototype threshold.",
            "data_mode": "synthetic",
        }]
        self._audit = AuditLog()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _validate_value(value: Any) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("threshold value must be a finite number")
        if not 0 <= value <= 100:
            raise ValueError("threshold value must be between 0 and 100")

    def get_active(self) -> dict[str, Any]:
        active = [item for item in self._history if item["status"] == "ACTIVE"]
        if len(active) != 1:
            raise RuntimeError("threshold registry must have exactly one active version")
        return deepcopy(active[0])

    def get_history(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(item) for item in self._history)

    def update_threshold(
        self,
        *,
        value: float,
        changed_by: str,
        reason: str,
        expected_version: int,
    ) -> dict[str, Any]:
        self._validate_value(value)
        if not isinstance(changed_by, str) or not changed_by.strip():
            raise ValueError("changed_by must be a non-empty string")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")

        current = self.get_active()
        if expected_version != current["version"]:
            raise ValueError("threshold version conflict; refresh active version before updating")
        if float(value) == current["value"]:
            raise ValueError("new threshold value must differ from the active value")

        self._history[-1] = {**current, "status": "SUPERSEDED"}
        new_threshold = {
            "id": current["id"],
            "type": current["type"],
            "value": float(value),
            "score_scale": "priority_0_100",
            "version": current["version"] + 1,
            "status": "ACTIVE",
            "effective_at": self._now(),
            "changed_by": changed_by.strip(),
            "reason": reason.strip(),
            "data_mode": "synthetic",
        }
        self._history.append(new_threshold)
        audit_event = self._audit.append(
            actor_id=changed_by.strip(),
            event_type="THRESHOLD_UPDATED",
            object_type="Threshold",
            object_id=current["id"],
            source="threshold_manager",
            scope="bank_internal",
            correlation_id=current["id"],
            data_mode="synthetic",
            details={
                "previous_value": current["value"],
                "new_value": new_threshold["value"],
                "previous_version": current["version"],
                "new_version": new_threshold["version"],
                "reason": reason.strip(),
                "score_scale": "priority_0_100",
            },
        )
        return {
            "threshold": deepcopy(new_threshold),
            "audit_event": audit_event,
        }

    def audit_events(self) -> tuple[dict[str, Any], ...]:
        return self._audit.events()
