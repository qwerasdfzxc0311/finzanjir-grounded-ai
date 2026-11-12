from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AutomationSafetyPolicy:
    allowed_actions: frozenset[str]

    def __init__(self, *, allowed_actions: set[str] | frozenset[str]) -> None:
        if not isinstance(allowed_actions, (set, frozenset)):
            raise ValueError("allowed_actions must be a set of action names")
        if any(not isinstance(value, str) or not value.strip() for value in allowed_actions):
            raise ValueError("allowed_actions must contain non-empty strings")
        actions = frozenset(value.strip() for value in allowed_actions)
        if not actions:
            raise ValueError("at least one allowed automation action is required")
        object.__setattr__(self, "allowed_actions", actions)

    def authorize(
        self,
        *,
        action: str,
        reason: str,
        state: str = "authorized",
        kill_switch_enabled: bool = True,
        circuit_breaker_state: str = "closed",
    ) -> dict[str, Any]:
        if not isinstance(action, str) or action.strip() not in self.allowed_actions:
            raise ValueError("automation action is not allowed")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("automation reason is required")
        if not isinstance(kill_switch_enabled, bool):
            raise ValueError("kill_switch_enabled must be boolean")
        if not isinstance(circuit_breaker_state, str) or circuit_breaker_state not in {"closed", "open"}:
            raise ValueError("circuit_breaker_state must be closed or open")
        if not isinstance(state, str):
            raise ValueError("state must be a string")
        if not kill_switch_enabled:
            return {"status": "SAFE_STOP", "route": "human_review", "reason": "kill_switch_disabled"}
        if circuit_breaker_state == "open":
            return {"status": "SAFE_STOP", "route": "human_review", "reason": "circuit_breaker_open"}
        if state in {"uncertain", "timeout"}:
            return {"status": "SAFE_STOP", "route": "human_review"}
        if state != "authorized":
            raise ValueError("unsupported automation state")
        return {
            "status": "AUTHORIZED",
            "action": action.strip(),
            "reason": reason.strip(),
        }


@dataclass
class AutomationCircuitBreaker:
    """Prototype in-memory circuit breaker; reset requires a distinct approver."""

    failure_threshold: int = 3
    _failure_count: int = field(default=0, init=False, repr=False)
    _state: str = field(default="closed", init=False, repr=False)
    _tripped_by: str | None = field(default=None, init=False, repr=False)
    _history: list[dict[str, str]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.failure_threshold, int) or isinstance(self.failure_threshold, bool) or self.failure_threshold < 1:
            raise ValueError("failure_threshold must be a positive integer")

    @property
    def state(self) -> str:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def record_failure(self, *, actor: str, reason: str) -> dict[str, Any]:
        if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
            raise ValueError("actor and reason are required")
        if self._state == "open":
            return {"state": "open", "failure_count": self._failure_count, "tripped": False}
        self._failure_count += 1
        tripped = self._failure_count >= self.failure_threshold
        if tripped:
            self._state = "open"
            self._tripped_by = actor.strip()
        self._history.append({"event": "failure", "actor": actor.strip(), "reason": reason.strip()})
        return {"state": self._state, "failure_count": self._failure_count, "tripped": tripped}

    def record_success(self) -> dict[str, Any]:
        if self._state == "open":
            return {"state": "open", "failure_count": self._failure_count, "reset": False}
        self._failure_count = 0
        return {"state": "closed", "failure_count": 0, "reset": True}

    def reset(self, *, approved_by: str, reason: str) -> dict[str, Any]:
        if self._state != "open":
            raise ValueError("circuit breaker is not open")
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ValueError("approved_by is required")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reset reason is required")
        if approved_by.strip() == self._tripped_by:
            raise ValueError("circuit breaker reset requires a distinct approver")
        self._history.append({"event": "manual_reset", "actor": approved_by.strip(), "reason": reason.strip()})
        self._state = "closed"
        self._failure_count = 0
        self._tripped_by = None
        return {"state": "closed", "failure_count": 0, "reset": True}

    def history(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(item) for item in self._history)
