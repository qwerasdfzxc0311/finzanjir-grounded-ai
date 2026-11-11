from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finzanjir_ai.knowledge.index import KnowledgeIndex
from .hybrid import RetrievalResult


# Canonical v0.6 uses several evidence states. Only states that are already
# grounded in an identified source/project authority may support an answer.
# Review, proposal, unverified, or source-dependent records must not be
# presented as confirmed facts by the answer layer.
GROUNDED_EVIDENCE_STATUSES = frozenset({
    "established",
    "project_source",
    "source_derived",
    "supported",
})


def is_grounded_evidence(evidence: Any) -> bool:
    return (
        isinstance(evidence, dict)
        and evidence.get("status") in GROUNDED_EVIDENCE_STATUSES
    )


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
    # A two-token query such as "FINZANJIR nima?" can legitimately yield
    # 0.50 lexical overlap from the authoritative FINZANJIR record. The
    # boundary must reject genuinely weak matches without discarding valid
    # short queries. Authoritative evidence is still required below.
    MIN_LEXICAL_RELEVANCE = 0.35

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
            if not is_grounded_evidence(record.evidence):
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
