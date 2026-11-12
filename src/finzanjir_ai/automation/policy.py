from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AutomationSafetyPolicy:
    allowed_actions: frozenset[str]

    def __init__(self, *, allowed_actions: set[str] | frozenset[str]) -> None:
        actions = frozenset(
            value.strip() for value in allowed_actions
            if isinstance(value, str) and value.strip()
        )
        if not actions:
            raise ValueError("at least one allowed automation action is required")
        object.__setattr__(self, "allowed_actions", actions)

    def authorize(
        self,
        *,
        action: str,
        reason: str,
        state: str = "authorized",
    ) -> dict[str, Any]:
        if not isinstance(action, str) or action.strip() not in self.allowed_actions:
            raise ValueError("automation action is not allowed")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("automation reason is required")
        if state in {"uncertain", "timeout"}:
            return {"status": "SAFE_STOP", "route": "human_review"}
        if state != "authorized":
            raise ValueError("unsupported automation state")
        return {
            "status": "AUTHORIZED",
            "action": action.strip(),
            "reason": reason.strip(),
        }
