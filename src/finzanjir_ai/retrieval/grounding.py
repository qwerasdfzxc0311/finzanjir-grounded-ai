from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finzanjir_ai.knowledge.index import KnowledgeIndex
from .hybrid import RetrievalResult


@dataclass(frozen=True)
class GroundedContextItem:
    record_id: str
    concept_id: str
    statement: str
    score: float
    provenance: tuple[Any, ...]
    evidence: Any


@dataclass(frozen=True)
class GroundedContext:
    items: tuple[GroundedContextItem, ...]


class GroundedContextAssembler:
    MIN_LEXICAL_RELEVANCE = 0.51

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def assemble(self, results: tuple[RetrievalResult, ...], *, max_items: int = 8) -> GroundedContext:
        items = []
        for result in results:
            if result.lexical_score < self.MIN_LEXICAL_RELEVANCE:
                continue
            record = self.index.get_record(result.record_id)
            if record is None:
                continue
            evidence_status = None
            if isinstance(record.evidence, dict):
                evidence_status = record.evidence.get("status")
            if evidence_status in {"rejected", "invalid"}:
                continue
            items.append(GroundedContextItem(
                record_id=record.record_id,
                concept_id=record.concept_id,
                statement=record.statement,
                score=result.score,
                provenance=record.provenance,
                evidence=record.evidence,
            ))
            if len(items) >= max_items:
                break
        return GroundedContext(items=tuple(items))
