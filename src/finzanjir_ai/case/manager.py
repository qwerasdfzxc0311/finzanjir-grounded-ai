from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class CaseManager:
    def __init__(self) -> None:
        self._cases: dict[str, dict[str, Any]] = {}
        self._human_decisions: dict[str, dict[str, Any]] = {}
        self._bank_statuses: dict[str, dict[str, Any]] = {}
        self._citizen_statuses: dict[str, dict[str, Any]] = {}
        self._audit_events: dict[str, dict[str, Any]] = {}

    def open_case(
        self,
        *,
        case_id: str,
        signal_ids: list[str],
        risk_id: str,
        threshold_id: str,
        transaction_id: str,
        escalation_met: bool,
    ) -> dict[str, Any]:
        if not escalation_met:
            raise ValueError("Case cannot open when escalation threshold is not met")
        if case_id in self._cases:
            raise ValueError(f"Case already exists: {case_id}")
        if not signal_ids or any(not isinstance(value, str) or not value.strip() for value in signal_ids):
            raise ValueError("Case requires at least one signal reference")
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        case = {
            "case_id": case_id,
            "source_signal_ids": list(signal_ids),
            "risk_id": risk_id,
            "threshold_id": threshold_id,
            "transaction_id": transaction_id,
            "status": "OPEN",
            "created_at": created_at,
        }
        self._cases[case_id] = case
        return dict(case)

    def get_case(self, case_id: str) -> dict[str, Any]:
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case: {case_id}")
        return dict(case)

    def get_human_decision(self, decision_id: str) -> dict[str, Any]:
        decision = self._human_decisions.get(decision_id)
        if decision is None:
            raise ValueError(f"Unknown human decision: {decision_id}")
        return dict(decision)

    def get_bank_status(self, case_id: str) -> dict[str, Any]:
        status = self._bank_statuses.get(case_id)
        if status is None:
            raise ValueError(f"Unknown bank status for case: {case_id}")
        return dict(status)

    def get_citizen_status(self, case_id: str) -> dict[str, Any]:
        status = self._citizen_statuses.get(case_id)
        if status is None:
            raise ValueError(f"Unknown citizen status for case: {case_id}")
        return dict(status)

    def get_audit_event(self, audit_id: str) -> dict[str, Any]:
        event = self._audit_events.get(audit_id)
        if event is None:
            raise ValueError(f"Unknown audit event: {audit_id}")
        return dict(event)

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
            "decision_id": f"decision-{case_id}",
            "case_id": case_id,
            "actor_id": actor_id,
            "decision": decision,
            "decided_at": decided_at,
            "reason": reason,
        }
        case["status"] = "ACTIONED" if decision == "APPROVE_ACTION" else "DISMISSED"

        bank_status = {
            "status_id": f"bank-status-{case_id}",
            "bank_id": "synthetic-demo",
            "case_id": case_id,
            "transaction_id": case["transaction_id"],
            "status": "REVIEW_REQUIRED" if decision == "APPROVE_ACTION" else "MONITORING",
            "updated_at": decided_at,
        }
        citizen_status = {
            "status_id": f"citizen-status-{case_id}",
            "actor_id": "authorized-subject",
            "case_id": case_id,
            "status": "UNDER_REVIEW" if decision == "APPROVE_ACTION" else "RESOLVED",
            "message": (
                "Tranzaksiyangiz bo‘yicha xavfsizlik tekshiruvi olib borilmoqda"
                if decision == "APPROVE_ACTION"
                else "Hodisa bo‘yicha tekshiruv yakunlandi"
            ),
            "updated_at": decided_at,
        }
        audit_event = {
            "audit_id": f"audit-{case_id}",
            "event_type": "HumanDecisionApplied",
            "actor_id": actor_id,
            "occurred_at": decided_at,
            "object_type": "HumanDecision",
            "object_id": human_decision["decision_id"],
            "change": {
                "decision": decision,
                "case_status": case["status"],
            },
        }
        self._human_decisions[human_decision["decision_id"]] = dict(human_decision)
        self._bank_statuses[case_id] = dict(bank_status)
        self._citizen_statuses[case_id] = dict(citizen_status)
        self._audit_events[audit_event["audit_id"]] = dict(audit_event)
        return {
            "case": dict(case),
            "human_decision": dict(human_decision),
            "bank_status": dict(bank_status),
            "citizen_status": dict(citizen_status),
            "audit_event": dict(audit_event),
        }
