from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class IncidentResponse:
    """In-memory incident lifecycle for synthetic prototype and control testing.

    This is not a durable production incident-management system. Real operations
    still require approved runbooks, owners, notification channels, forensic
    retention, and tested recovery infrastructure.
    """

    SEVERITIES = frozenset({"low", "medium", "high", "critical"})
    ACTION_TRANSITIONS = {
        "TRIAGED": {"OPEN": "TRIAGED"},
        "CONTAINED": {"OPEN": "CONTAINED", "TRIAGED": "CONTAINED"},
        "RECOVERY_STARTED": {"CONTAINED": "RECOVERING"},
        "RECOVERY_VERIFIED": {"RECOVERING": "RECOVERED"},
        "POST_INCIDENT_REVIEWED": {"RECOVERED": "REVIEWED"},
    }

    def __init__(self) -> None:
        self._incidents: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _evidence_refs(evidence: list[str] | None) -> list[str]:
        if evidence is None:
            return []
        if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise ValueError("evidence must be a list of non-empty references")
        return list(dict.fromkeys(item.strip() for item in evidence))

    def open_incident(
        self,
        *,
        incident_id: str,
        classification: str,
        severity: str,
        owner: str,
        next_step: str,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        incident_id = self._required_text(incident_id, "incident_id")
        classification = self._required_text(classification, "classification")
        owner = self._required_text(owner, "owner")
        next_step = self._required_text(next_step, "next_step")
        if not isinstance(severity, str) or severity.strip().lower() not in self.SEVERITIES:
            raise ValueError("severity must be low, medium, high or critical")
        if incident_id in self._incidents:
            raise ValueError(f"incident already exists: {incident_id}")

        now = self._now()
        incident = {
            "incident_id": incident_id,
            "classification": classification,
            "severity": severity.strip().lower(),
            "owner": owner,
            "next_step": next_step,
            "evidence": self._evidence_refs(evidence),
            "timeline": [{"event": "OPENED", "at": now, "actor": owner, "evidence": []}],
            "escalation_required": severity.strip().lower() in {"high", "critical"},
            "status": "OPEN",
            "opened_at": now,
            "closed_at": None,
        }
        self._incidents[incident_id] = deepcopy(incident)
        return deepcopy(incident)

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError(f"unknown incident: {incident_id}")
        return deepcopy(incident)

    def record_action(
        self,
        incident_id: str,
        *,
        action: str,
        actor: str,
        note: str,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError(f"unknown incident: {incident_id}")
        action = self._required_text(action, "action").upper()
        actor = self._required_text(actor, "actor")
        note = self._required_text(note, "note")
        evidence_refs = self._evidence_refs(evidence)
        transitions = self.ACTION_TRANSITIONS.get(action)
        if transitions is None:
            raise ValueError(f"unsupported incident action: {action}")
        next_status = transitions.get(incident["status"])
        if next_status is None:
            raise ValueError(f"action {action} is not allowed from {incident['status']}")
        if action == "RECOVERY_VERIFIED" and not evidence_refs:
            raise ValueError("recovery verification requires evidence references")

        now = self._now()
        updated = deepcopy(incident)
        updated["timeline"].append({
            "event": action,
            "at": now,
            "actor": actor,
            "note": note,
            "evidence": evidence_refs,
        })
        updated["evidence"] = list(dict.fromkeys([*updated["evidence"], *evidence_refs]))
        updated["status"] = next_status
        updated["next_step"] = note
        self._incidents[incident_id] = updated
        return deepcopy(updated)

    def close_incident(self, incident_id: str, *, recovery_verified: bool) -> dict[str, Any]:
        if not isinstance(recovery_verified, bool):
            raise ValueError("recovery_verified must be boolean")
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError(f"unknown incident: {incident_id}")
        if not recovery_verified or incident["status"] not in {"RECOVERED", "REVIEWED"}:
            return {
                "incident_id": incident_id,
                "closed": False,
                "reason": "recovery_not_verified",
                "incident_retained": True,
                "status": incident["status"],
            }

        now = self._now()
        updated = deepcopy(incident)
        updated["timeline"].append({
            "event": "CLOSED",
            "at": now,
            "actor": updated["owner"],
            "evidence": [],
        })
        updated["status"] = "CLOSED"
        updated["closed_at"] = now
        self._incidents[incident_id] = updated
        return {
            "incident_id": incident_id,
            "closed": True,
            "reason": "recovery_verified",
            "incident_retained": True,
            "status": "CLOSED",
            "timeline": deepcopy(updated["timeline"]),
        }
