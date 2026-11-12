from datetime import datetime, timezone
from typing import Any


class IncidentResponse:
    """Create auditable incident records and require verified recovery before closure."""

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
        if not incident_id or not classification or not owner or not next_step:
            raise ValueError("incident_id, classification, owner and next_step are required")

        now = datetime.now(timezone.utc).isoformat()
        return {
            "incident_id": incident_id,
            "classification": classification,
            "severity": severity,
            "owner": owner,
            "next_step": next_step,
            "evidence": list(evidence or []),
            "timeline": [{"event": "opened", "at": now}],
            "escalation_required": severity.lower() in {"high", "critical"},
            "status": "OPEN",
        }

    def close_incident(self, incident_id: str, *, recovery_verified: bool) -> dict[str, Any]:
        if not recovery_verified:
            return {
                "incident_id": incident_id,
                "closed": False,
                "reason": "recovery_not_verified",
                "incident_retained": True,
            }
        return {
            "incident_id": incident_id,
            "closed": True,
            "reason": "recovery_verified",
            "incident_retained": True,
        }
