from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class CaseManager:
    def __init__(self) -> None:
        self._cases: dict[str, dict[str, Any]] = {}

    def open_case(
        self,
        *,
        case_id: str,
        signal_ids: list[str],
        risk_id: str,
        threshold_id: str,
        escalation_met: bool,
    ) -> dict[str, Any]:
        if not escalation_met:
            raise ValueError("Case cannot open when escalation threshold is not met")
        if case_id in self._cases:
            raise ValueError(f"Case already exists: {case_id}")
        case = {
            "id": case_id,
            "signal_ids": list(signal_ids),
            "risk_id": risk_id,
            "threshold_id": threshold_id,
            "status": "OPEN",
            "opened_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        self._cases[case_id] = case
        return dict(case)

    def apply_human_decision(
        self,
        *,
        case_id: str,
        actor_id: str,
        decision: str,
        reason: str,
    ) -> dict[str, Any]:
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case: {case_id}")
        if case["status"] not in {"OPEN", "IN_REVIEW"}:
            raise ValueError(f"Case is not reviewable: {case['status']}")

        decided_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        human_decision = {
            "id": f"decision-{case_id}",
            "case_id": case_id,
            "actor_id": actor_id,
            "decision": decision,
            "decided_at": decided_at,
            "reason": reason,
        }
        case["status"] = "ACTIONED" if decision == "APPROVE_ACTION" else "DISMISSED"

        bank_status = {
            "id": f"bank-status-{case_id}",
            "case_id": case_id,
            "bank_id": "synthetic-demo",
            "status": "REVIEW_REQUIRED" if decision == "APPROVE_ACTION" else "MONITORING",
            "updated_at": decided_at,
        }
        citizen_status = {
            "id": f"citizen-status-{case_id}",
            "case_id": case_id,
            "citizen_id": "authorized-subject",
            "status": "UNDER_REVIEW" if decision == "APPROVE_ACTION" else "RESOLVED",
            "updated_at": decided_at,
        }
        audit_event = {
            "id": f"audit-{case_id}",
            "case_id": case_id,
            "event_type": "HumanDecisionApplied",
            "actor_id": actor_id,
            "occurred_at": decided_at,
            "object_type": "HumanDecision",
            "object_id": human_decision["id"],
            "details": {"decision": decision, "case_status": case["status"]},
        }
        return {
            "case": dict(case),
            "human_decision": human_decision,
            "bank_status": bank_status,
            "citizen_status": citizen_status,
            "audit_event": audit_event,
        }
