from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
from typing import Any, Callable, Mapping, Protocol, Sequence

import httpx

from finzanjir_ai.answer.providers import LLMGateway


class WorkerRole(str, Enum):
    LANGUAGE = "language"
    RESEARCH = "research"
    CRITIC = "critic"
    EDITOR = "editor"
    SPECIALIST = "specialist"


class DataClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"


@dataclass(frozen=True)
class CloudTask:
    text: str
    data_class: DataClass = DataClass.SENSITIVE
    user_approved: bool = False
    legal_basis_ref: str | None = None


@dataclass(frozen=True)
class CloudPolicy:
    """Default-deny policy for optional cloud workers."""

    enabled: bool = False
    approved_data_classes: frozenset[DataClass] = frozenset()
    legal_reviewed_data_classes: frozenset[DataClass] = frozenset()
    max_workers_per_task: int = 2
    require_user_approval: bool = True

    def permits(self, task: CloudTask) -> bool:
        if not self.enabled or task.data_class not in self.approved_data_classes:
            return False
        if self.require_user_approval and not task.user_approved:
            return False
        if task.data_class != DataClass.PUBLIC:
            if task.data_class not in self.legal_reviewed_data_classes:
                return False
            if not (task.legal_basis_ref or "").strip():
                return False
        # This is a conservative identifier deny-list, not full DLP. It is
        # an additional block, never a substitute for data classification.
        return LLMGateway.can_send_text(task.text)


@dataclass(frozen=True)
class WorkerOutcome:
    worker_name: str
    role: WorkerRole
    output: str
    status: str
    untrusted: bool = True


class WorkerAdapter(Protocol):
    name: str
    role: WorkerRole

    def execute(self, task: CloudTask) -> str: ...


@dataclass
class JsonHttpWorkerAdapter:
    """Provider-neutral JSON-over-HTTPS adapter with provider-specific mappers.

    The request/response mappers are supplied by each provider integration.
    This class never logs prompts, response bodies, or credentials.
    """

    name: str
    role: WorkerRole
    endpoint: str
    api_key_env: str
    request_builder: Callable[[CloudTask], Mapping[str, Any]]
    response_parser: Callable[[Mapping[str, Any]], str]
    environ: Mapping[str, str] | None = None
    timeout_seconds: float = 12.0
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    transport: httpx.BaseTransport | None = field(default=None, repr=False)

    def execute(self, task: CloudTask) -> str:
        if not self.endpoint.startswith("https://"):
            raise ValueError("Cloud worker endpoint must use HTTPS")
        environment = self.environ if self.environ is not None else os.environ
        api_key = str(environment.get(self.api_key_env, "")).strip()
        if not api_key:
            raise RuntimeError("Cloud worker is not configured")
        timeout = httpx.Timeout(self.timeout_seconds, connect=min(5.0, self.timeout_seconds))
        headers = {
            self.auth_header: self.auth_prefix + api_key,
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=timeout, transport=self.transport) as client:
            response = client.post(
                self.endpoint,
                headers=headers,
                json=dict(self.request_builder(task)),
            )
            response.raise_for_status()
            body = response.json()
        output = self.response_parser(body)
        if not isinstance(output, str) or not output.strip():
            raise ValueError("Cloud worker returned no usable text")
        return output.strip()[:12000]


class CloudWorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[WorkerRole, list[WorkerAdapter]] = {}

    def register(self, adapter: WorkerAdapter) -> None:
        workers = self._workers.setdefault(adapter.role, [])
        if any(worker.name == adapter.name for worker in workers):
            raise ValueError(f"Duplicate cloud worker name for role: {adapter.name}")
        workers.append(adapter)

    def first_for_role(self, role: WorkerRole) -> WorkerAdapter | None:
        workers = self._workers.get(role, [])
        return workers[0] if workers else None


class CloudWorkerRouter:
    """Runs only explicitly requested roles; local-first and default-deny."""

    def __init__(
        self,
        registry: CloudWorkerRegistry,
        policy: CloudPolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or CloudPolicy()

    def dispatch(
        self,
        task: CloudTask,
        roles: Sequence[WorkerRole],
    ) -> tuple[WorkerOutcome, ...]:
        if not self.policy.permits(task):
            return ()
        unique_roles = tuple(dict.fromkeys(roles))
        limit = max(0, min(int(self.policy.max_workers_per_task), 2))
        outcomes: list[WorkerOutcome] = []
        for role in unique_roles[:limit]:
            adapter = self.registry.first_for_role(role)
            if adapter is None:
                continue
            try:
                output = adapter.execute(task)
            except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError):
                outcomes.append(WorkerOutcome(
                    worker_name=adapter.name,
                    role=role,
                    output="",
                    status="worker_failed",
                ))
                continue
            outcomes.append(WorkerOutcome(
                worker_name=adapter.name,
                role=role,
                output=output,
                status="ready",
            ))
        return tuple(outcomes)
