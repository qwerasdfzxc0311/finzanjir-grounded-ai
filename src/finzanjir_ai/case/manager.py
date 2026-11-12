from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class CaseManager:
    ALLOWED_HUMAN_DECISIONS = frozenset({"APPROVE_ACTION", "DISMISS"})

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
        transaction_id: str = "derived-from-case",
        bank_id: str = "synthetic-demo",
        citizen_id: str = "synthetic-subject",
        escalation_met: bool,
        data_mode: str = "synthetic",
    ) -> dict[str, Any]:
        if not escalation_met:
            raise ValueError("Case cannot open when escalation threshold is not met")
        if not isinstance(bank_id, str) or not bank_id.strip():
            raise ValueError("bank_id must be a non-empty string")
        if not isinstance(citizen_id, str) or not citizen_id.strip():
            raise ValueError("citizen_id must be a non-empty string")
        if data_mode not in {"synthetic", "real", "unknown"}:
            raise ValueError("data_mode must be synthetic, real, or unknown")
        if case_id in self._cases:
            raise ValueError(f"Case already exists: {case_id}")
        if not signal_ids or any(not isinstance(value, str) or not value.strip() for value in signal_ids):
            raise ValueError("Case requires at least one signal reference")
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        case = {
            "id": case_id,
            "case_id": case_id,
            "signal_ids": list(signal_ids),
            "source_signal_ids": list(signal_ids),
            "risk_id": risk_id,
            "threshold_id": threshold_id,
            "transaction_id": transaction_id,
            "bank_id": bank_id.strip(),
            "citizen_id": citizen_id.strip(),
            "data_mode": data_mode,
            "status": "OPEN",
            "opened_at": created_at,
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
        decision_origin: str = "human_review",
        actor_type: str = "authorized_human",
        is_authoritative: bool = True,
    ) -> dict[str, Any]:
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case: {case_id}")
        if case["status"] not in {"OPEN", "IN_REVIEW"}:
            raise ValueError(f"Case is not reviewable: {case['status']}")
        if decision not in self.ALLOWED_HUMAN_DECISIONS:
            raise ValueError(f"Unsupported human decision: {decision}")
        if not isinstance(actor_id, str) or not actor_id.strip() or not isinstance(reason, str) or not reason.strip():
            raise ValueError("Human decision requires non-empty actor_id and reason")
        if not isinstance(decision_origin, str) or not decision_origin.strip():
            raise ValueError("decision_origin must be non-empty")
        if not isinstance(actor_type, str) or not actor_type.strip():
            raise ValueError("actor_type must be non-empty")
        if not isinstance(is_authoritative, bool):
            raise ValueError("is_authoritative must be boolean")
        if decision_origin == "synthetic_demo" or actor_type == "synthetic_demo":
            if decision_origin != "synthetic_demo" or actor_type != "synthetic_demo" or is_authoritative:
                raise ValueError("synthetic_demo decision must be non-authoritative")
        elif not is_authoritative and decision_origin == "human_review":
            raise ValueError("human_review decision cannot be non-authoritative")

        decided_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        prior_decisions = sum(1 for item in self._human_decisions.values() if item["case_id"] == case_id)
        decision_suffix = "" if prior_decisions == 0 else f"-{prior_decisions + 1}"
        decision_id = f"decision-{case_id}{decision_suffix}"
        human_decision = {
            "id": decision_id,
            "decision_id": decision_id,
            "case_id": case_id,
            "actor_id": actor_id.strip(),
            "decision": decision,
            "decided_at": decided_at,
            "reason": reason.strip(),
            "decision_origin": decision_origin.strip(),
            "actor_type": actor_type.strip(),
            "is_authoritative": is_authoritative,
            "data_mode": case["data_mode"],
        }
        if is_authoritative:
            case["status"] = "ACTIONED" if decision == "APPROVE_ACTION" else "DISMISSED"

        bank_status = None
        citizen_status = None
        if is_authoritative:
            bank_status = {
                "id": f"bank-status-{case_id}",
                "status_id": f"bank-status-{case_id}",
                "bank_id": case["bank_id"],
                "case_id": case_id,
                "transaction_id": case["transaction_id"],
                "status": "REVIEW_REQUIRED" if decision == "APPROVE_ACTION" else "MONITORING",
                "updated_at": decided_at,
                "data_mode": case["data_mode"],
            }
            citizen_status = {
                "id": f"citizen-status-{case_id}",
                "status_id": f"citizen-status-{case_id}",
                "actor_id": case["citizen_id"],
                "citizen_id": case["citizen_id"],
                "case_id": case_id,
                "status": "UNDER_REVIEW" if decision == "APPROVE_ACTION" else "RESOLVED",
                "message": (
                    "Tranzaksiyangiz bo‘yicha xavfsizlik tekshiruvi olib borilmoqda"
                    if decision == "APPROVE_ACTION"
                    else "Hodisa bo‘yicha tekshiruv yakunlandi"
                ),
                "updated_at": decided_at,
                "data_mode": case["data_mode"],
            }

        change = {
            "decision": decision,
            "case_status": case["status"],
            "decision_origin": decision_origin.strip(),
            "actor_type": actor_type.strip(),
            "is_authoritative": is_authoritative,
        }
        audit_id = f"audit-{uuid4().hex}"
        audit_event = {
            "id": audit_id,
            "event_id": audit_id,
            "audit_id": audit_id,
            "event_type": "HumanDecisionApplied",
            "actor_id": actor_id.strip(),
            "occurred_at": decided_at,
            "source": "case_manager",
            "scope": "bank_internal",
            "object_type": "HumanDecision",
            "object_id": human_decision["decision_id"],
            "correlation_id": case["transaction_id"],
            "causation_id": None,
            "payload": {"case_id": case_id, **change},
            "details": {"case_id": case_id, **change},
            "data_mode": case["data_mode"],
            "schema_version": "event-envelope-v2",
            "case_id": case_id,
            "change": change,
        }
        self._human_decisions[human_decision["decision_id"]] = dict(human_decision)
        if bank_status is not None and citizen_status is not None:
            self._bank_statuses[case_id] = dict(bank_status)
            self._citizen_statuses[case_id] = dict(citizen_status)
        self._audit_events[audit_event["audit_id"]] = dict(audit_event)
        return {
            "case": dict(case),
            "human_decision": dict(human_decision),
            "bank_status": bank_status,
            "citizen_status": citizen_status,
            "audit_event": dict(audit_event),
        }
