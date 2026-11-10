from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class KnowledgeChangeControl:
    def __init__(self, *, current_version: str) -> None:
        self.current_version = current_version
        self._candidates: dict[str, dict[str, Any]] = {}

    def propose(self, *, statement: str, provenance: tuple[str, ...]) -> dict[str, Any]:
        if not statement.strip():
            raise ValueError("statement is required")
        candidate = {
            "candidate_id": f"cand-{uuid4().hex[:12]}",
            "statement": statement,
            "provenance": tuple(provenance),
            "status": "PENDING_REVIEW",
            "target_version": f"{self.current_version}-candidate",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        self._candidates[candidate["candidate_id"]] = candidate
        return dict(candidate)

    def write_authoritative(self, candidate: dict[str, Any]) -> None:
        raise PermissionError("AI cannot write authoritative knowledge directly")

    def approve(self, candidate_id: str, *, reviewer_id: str) -> dict[str, Any]:
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            raise ValueError(f"Unknown candidate: {candidate_id}")
        if not reviewer_id.strip():
            raise ValueError("reviewer_id is required")
        approved = dict(candidate)
        approved["status"] = "APPROVED"
        approved["reviewer_id"] = reviewer_id
        approved["target_version"] = "v0.7"
        approved["approved_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._candidates[candidate_id] = approved
        return dict(approved)
