from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class CitizenAppealRegistry:
    """Synthetic-only in-memory appeal/correction workflow.

    It records a request and reviewer response but never changes a bank Case,
    payment state, account restriction, or authoritative citizen record.
    """

    REQUEST_TYPES = frozenset({"REVIEW", "CORRECTION"})
    OUTCOMES = {
        "REVIEW": frozenset({"UPHELD", "DISMISSED", "NEED_MORE_INFO"}),
        "CORRECTION": frozenset({"UPHELD", "DISMISSED", "NEED_MORE_INFO", "CORRECTED"}),
    }

    def __init__(self) -> None:
        self._appeals: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _required_text(value: Any, field: str, *, max_length: int = 512) -> str:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
            raise ValueError(f"{field} must be a non-empty string up to {max_length} characters")
        return value.strip()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @classmethod
    def _references(cls, values: list[str] | None, field: str) -> list[str]:
        if values is None:
            return []
        if not isinstance(values, list) or len(values) > 20:
            raise ValueError(f"{field} must be a list of at most 20 opaque references")
        normalized = [cls._required_text(item, field, max_length=256) for item in values]
        return list(dict.fromkeys(normalized))

    def submit(
        self,
        *,
        case_id: str,
        citizen_ref: str,
        request_type: str,
        reason: str,
        evidence_refs: list[str] | None = None,
        data_mode: str = "synthetic",
    ) -> dict[str, Any]:
        case_id = self._required_text(case_id, "case_id")
        citizen_ref = self._required_text(citizen_ref, "citizen_ref")
        request_type = self._required_text(request_type, "request_type").upper()
        reason = self._required_text(reason, "reason", max_length=2000)
        if request_type not in self.REQUEST_TYPES:
            raise ValueError("request_type must be REVIEW or CORRECTION")
        if data_mode != "synthetic":
            raise ValueError("appeal registry currently accepts synthetic data only")
        evidence = self._references(evidence_refs, "evidence_refs")
        now = self._now()
        appeal_id = f"appeal-{uuid4().hex}"
        appeal = {
            "appeal_id": appeal_id,
            "case_id": case_id,
            "citizen_ref": citizen_ref,
            "request_type": request_type,
            "reason": reason,
            "evidence_refs": evidence,
            "data_mode": "synthetic",
            "status": "SUBMITTED",
            "submitted_at": now,
            "assigned_reviewer": None,
            "outcome": None,
            "response": None,
            "correction_reference": None,
            "timeline": [{"event": "SUBMITTED", "at": now}],
        }
        self._appeals[appeal_id] = deepcopy(appeal)
        return deepcopy(appeal)

    def get(self, appeal_id: str) -> dict[str, Any]:
        appeal = self._appeals.get(appeal_id)
        if appeal is None:
            raise ValueError(f"unknown appeal: {appeal_id}")
        return deepcopy(appeal)

    def assign_reviewer(
        self,
        appeal_id: str,
        *,
        reviewer_ref: str,
        reviewer_authorized: bool,
    ) -> dict[str, Any]:
        appeal = self._appeals.get(appeal_id)
        if appeal is None:
            raise ValueError(f"unknown appeal: {appeal_id}")
        if not isinstance(reviewer_authorized, bool) or reviewer_authorized is not True:
            raise ValueError("reviewer authorization is required")
        reviewer_ref = self._required_text(reviewer_ref, "reviewer_ref")
        if appeal["status"] != "SUBMITTED":
            raise ValueError(f"appeal cannot be assigned from {appeal['status']}")
        now = self._now()
        updated = deepcopy(appeal)
        updated["assigned_reviewer"] = reviewer_ref
        updated["status"] = "IN_REVIEW"
        updated["timeline"].append({"event": "ASSIGNED", "at": now, "reviewer_ref": reviewer_ref})
        self._appeals[appeal_id] = updated
        return deepcopy(updated)

    def respond(
        self,
        appeal_id: str,
        *,
        reviewer_ref: str,
        outcome: str,
        response: str,
        reviewer_authorized: bool,
        correction_reference: str | None = None,
    ) -> dict[str, Any]:
        appeal = self._appeals.get(appeal_id)
        if appeal is None:
            raise ValueError(f"unknown appeal: {appeal_id}")
        if not isinstance(reviewer_authorized, bool) or reviewer_authorized is not True:
            raise ValueError("reviewer authorization is required")
        reviewer_ref = self._required_text(reviewer_ref, "reviewer_ref")
        outcome = self._required_text(outcome, "outcome").upper()
        response = self._required_text(response, "response", max_length=2000)
        if appeal["status"] != "IN_REVIEW":
            raise ValueError(f"appeal cannot be answered from {appeal['status']}")
        if reviewer_ref != appeal["assigned_reviewer"]:
            raise ValueError("only the assigned reviewer may respond")
        if outcome not in self.OUTCOMES[appeal["request_type"]]:
            raise ValueError("outcome is not allowed for this request type")
        correction_ref = None
        if outcome == "CORRECTED":
            if appeal["request_type"] != "CORRECTION":
                raise ValueError("only a correction request may have CORRECTED outcome")
            correction_ref = self._required_text(correction_reference, "correction_reference")
        elif correction_reference is not None:
            raise ValueError("correction_reference is only allowed for CORRECTED outcome")

        now = self._now()
        updated = deepcopy(appeal)
        updated["outcome"] = outcome
        updated["response"] = response
        updated["correction_reference"] = correction_ref
        updated["status"] = "RESPONDED"
        updated["timeline"].append({
            "event": "RESPONDED",
            "at": now,
            "reviewer_ref": reviewer_ref,
            "outcome": outcome,
        })
        self._appeals[appeal_id] = updated
        return deepcopy(updated)
