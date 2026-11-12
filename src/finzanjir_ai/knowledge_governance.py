from typing import Any


class KnowledgeGovernance:
    """Keep AI claims tied to evidence and separate candidate from authoritative knowledge."""

    def answer(
        self,
        *,
        claim: str,
        source: str | None,
        evidence_sufficient: bool,
        conflicting_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        conflicts = list(conflicting_sources or [])
        if conflicts:
            return {
                "claim": None,
                "source": source,
                "status": "conflict",
                "conflicting_sources": conflicts,
                "limitation": "Sources conflict; the claim cannot be presented as an established fact.",
            }
        if not source or not evidence_sufficient:
            return {
                "claim": None,
                "source": source,
                "status": "insufficient_evidence",
                "limitation": "Available evidence is insufficient to support the claim.",
            }
        return {
            "claim": claim,
            "source": source,
            "status": "supported",
            "limitation": None,
        }

    def promote_candidate(self, *, candidate: dict[str, Any], authorized: bool) -> dict[str, Any]:
        if not authorized:
            return {
                "approved": False,
                "status": "approval_required",
                "candidate": dict(candidate),
            }
        return {
            "approved": True,
            "status": "approved",
            "candidate": dict(candidate),
        }
