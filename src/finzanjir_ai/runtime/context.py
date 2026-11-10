from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeContext:
    knowledge_refs: tuple[str, ...]
    runtime_refs: tuple[str, ...]
    working_memory_scope: str
    can_write_authoritative_knowledge: bool = False

    @classmethod
    def from_refs(cls, *, knowledge_refs: tuple[str, ...], runtime_refs: tuple[str, ...], working_memory_scope: str) -> "RuntimeContext":
        if not working_memory_scope.strip():
            raise ValueError("working_memory_scope is required")
        return cls(
            knowledge_refs=tuple(knowledge_refs),
            runtime_refs=tuple(runtime_refs),
            working_memory_scope=working_memory_scope,
        )
