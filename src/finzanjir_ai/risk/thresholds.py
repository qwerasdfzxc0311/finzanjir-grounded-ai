from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any
from uuid import uuid4

from finzanjir_ai.audit.service import AuditLog


class ThresholdManager:
    """In-memory, versioned threshold governance for synthetic prototype flows.

    Threshold changes require a proposal and a distinct approver. This is not
    production RBAC or durable governance storage.
    """

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
        self._proposals: dict[str, dict[str, Any]] = {}
        self._audit = AuditLog()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _validate_value(value: Any) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("threshold value must be a finite number")
        if not 0 <= value <= 100:
            raise ValueError("threshold value must be between 0 and 100")

    @staticmethod
    def _validate_version(value: Any) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("expected_version must be a positive integer")

    def get_active(self) -> dict[str, Any]:
        active = [item for item in self._history if item["status"] == "ACTIVE"]
        if len(active) != 1:
            raise RuntimeError("threshold registry must have exactly one active version")
        return deepcopy(active[0])

    def get_history(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(item) for item in self._history)

    def get_proposals(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(item) for item in self._proposals.values())

    def propose_threshold(
        self,
        *,
        value: float,
        proposed_by: str,
        reason: str,
        expected_version: int,
    ) -> dict[str, Any]:
        self._validate_value(value)
        proposed_by = self._required_text(proposed_by, "proposed_by")
        reason = self._required_text(reason, "reason")
        self._validate_version(expected_version)
        current = self.get_active()
        if expected_version != current["version"]:
            raise ValueError("threshold version conflict; refresh active version before proposing")
        if float(value) == current["value"]:
            raise ValueError("new threshold value must differ from the active value")

        proposal_id = f"threshold-proposal-{uuid4().hex}"
        now = self._now()
        audit_event = self._audit.append(
            actor_id=proposed_by,
            event_type="THRESHOLD_PROPOSED",
            object_type="ThresholdProposal",
            object_id=proposal_id,
            source="threshold_manager",
            scope="bank_internal",
            correlation_id=current["id"],
            data_mode="synthetic",
            details={
                "proposal_id": proposal_id,
                "proposed_value": float(value),
                "expected_version": expected_version,
                "reason": reason,
                "score_scale": "priority_0_100",
            },
        )
        proposal = {
            "proposal_id": proposal_id,
            "threshold_id": current["id"],
            "proposed_value": float(value),
            "proposed_by": proposed_by,
            "reason": reason,
            "expected_version": expected_version,
            "status": "PENDING",
            "created_at": now,
            "approved_by": None,
            "approved_at": None,
            "resulting_version": None,
            "data_mode": "synthetic",
            "audit_event_id": audit_event["event_id"],
        }
        self._proposals[proposal_id] = proposal
        return {"proposal": deepcopy(proposal), "audit_event": audit_event}

    def approve_proposal(self, proposal_id: str, *, approved_by: str) -> dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"unknown threshold proposal: {proposal_id}")
        if proposal["status"] != "PENDING":
            raise ValueError(f"threshold proposal is not pending: {proposal['status']}")
        approved_by = self._required_text(approved_by, "approved_by")
        if approved_by == proposal["proposed_by"]:
            raise ValueError("threshold proposal requires a distinct approver")

        current = self.get_active()
        if current["version"] != proposal["expected_version"]:
            raise ValueError("threshold version conflict; proposal must be re-created")
        new_threshold = {
            "id": current["id"],
            "type": current["type"],
            "value": proposal["proposed_value"],
            "score_scale": "priority_0_100",
            "version": current["version"] + 1,
            "status": "ACTIVE",
            "effective_at": self._now(),
            "changed_by": approved_by,
            "reason": proposal["reason"],
            "data_mode": "synthetic",
        }
        # Audit first: if the audit write fails, active threshold and proposal stay unchanged.
        audit_event = self._audit.append(
            actor_id=approved_by,
            event_type="THRESHOLD_UPDATED",
            object_type="Threshold",
            object_id=current["id"],
            source="threshold_manager",
            scope="bank_internal",
            correlation_id=current["id"],
            data_mode="synthetic",
            details={
                "proposal_id": proposal_id,
                "proposed_by": proposal["proposed_by"],
                "approved_by": approved_by,
                "previous_value": current["value"],
                "new_value": new_threshold["value"],
                "previous_version": current["version"],
                "new_version": new_threshold["version"],
                "reason": proposal["reason"],
                "score_scale": "priority_0_100",
            },
        )
        self._history[-1] = {**current, "status": "SUPERSEDED"}
        self._history.append(new_threshold)
        updated_proposal = {
            **proposal,
            "status": "APPROVED",
            "approved_by": approved_by,
            "approved_at": self._now(),
            "resulting_version": new_threshold["version"],
            "approval_audit_event_id": audit_event["event_id"],
        }
        self._proposals[proposal_id] = updated_proposal
        return {
            "threshold": deepcopy(new_threshold),
            "proposal": deepcopy(updated_proposal),
            "audit_event": audit_event,
        }

    def reject_proposal(
        self,
        proposal_id: str,
        *,
        rejected_by: str,
        reason: str,
    ) -> dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"unknown threshold proposal: {proposal_id}")
        if proposal["status"] != "PENDING":
            raise ValueError(f"threshold proposal is not pending: {proposal['status']}")
        rejected_by = self._required_text(rejected_by, "rejected_by")
        reason = self._required_text(reason, "reason")
        if rejected_by == proposal["proposed_by"]:
            raise ValueError("threshold proposal requires a distinct reviewer")
        audit_event = self._audit.append(
            actor_id=rejected_by,
            event_type="THRESHOLD_PROPOSAL_REJECTED",
            object_type="ThresholdProposal",
            object_id=proposal_id,
            source="threshold_manager",
            scope="bank_internal",
            correlation_id=proposal["threshold_id"],
            data_mode="synthetic",
            details={"proposal_id": proposal_id, "proposed_by": proposal["proposed_by"], "reason": reason},
        )
        updated = {
            **proposal,
            "status": "REJECTED",
            "rejected_by": rejected_by,
            "rejected_at": self._now(),
            "rejection_reason": reason,
            "rejection_audit_event_id": audit_event["event_id"],
        }
        self._proposals[proposal_id] = updated
        return {"proposal": deepcopy(updated), "audit_event": audit_event}

    def update_threshold(self, **_kwargs: Any) -> dict[str, Any]:
        raise ValueError("direct threshold updates are disabled; use propose_threshold and approve_proposal")

    def audit_events(self) -> tuple[dict[str, Any], ...]:
        return self._audit.events()
