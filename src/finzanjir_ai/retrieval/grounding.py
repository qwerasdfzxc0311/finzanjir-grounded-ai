from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finzanjir_ai.knowledge.index import KnowledgeIndex
from .hybrid import RetrievalResult
from .text import meaningful_tokens


GROUNDED_EVIDENCE_STATUSES = frozenset({
    "established",
    "project_source",
    "source_derived",
    "supported",
})


def is_grounded_evidence(evidence: Any) -> bool:
    if not isinstance(evidence, dict) or evidence.get("status") not in GROUNDED_EVIDENCE_STATUSES:
        return False
    verification = evidence.get("verification")
    if isinstance(verification, str) and verification.casefold() in {"unconfirmed", "unverified", "rejected"}:
        return False
    if verification is False:
        return False
    return True


def is_grounded_record(evidence: Any, statement: str) -> bool:
    # Verification metadata is authoritative. Do not reject a supported
    # principle merely because its wording discusses uncertainty, proposals,
    # or unverified suspicions as a concept.
    return is_grounded_evidence(evidence)


@dataclass(frozen=True)
class GroundedContextItem:
    record_id: str
    concept_id: str
    statement: str
    score: float
    provenance: tuple[Any, ...]
    evidence: Any
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroundedContext:
    items: tuple[GroundedContextItem, ...]


class GroundedContextAssembler:
    MIN_LEXICAL_RELEVANCE = 0.50
    MIN_RETRIEVAL_SCORE = 0.38
    MIN_RELATIVE_QUERY_RELEVANCE = 0.82

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def assemble_entity(self, entity_id: str, *, max_items: int = 8) -> GroundedContext:
        """Resolve a canonical entity to its explicitly linked, verified fact records."""
        items = []
        for record in self.index.records_for_entity(entity_id):
            if not is_grounded_record(record.evidence, record.statement):
                continue
            items.append(GroundedContextItem(
                record_id=record.record_id,
                concept_id=record.concept_id,
                statement=record.statement,
                score=1.0,
                provenance=record.provenance,
                evidence=record.evidence,
                aliases=record.aliases,
            ))
            if len(items) >= max_items:
                break
        return GroundedContext(items=tuple(items))

    def assemble(
        self,
        results: tuple[RetrievalResult, ...],
        *,
        query: str | None = None,
        query_alternatives: tuple[str, ...] = (),
        max_items: int = 8,
    ) -> GroundedContext:
        items = []
        query_candidates = tuple(
            tokens for value in ((query or ""), *query_alternatives)
            if len(tokens := set(meaningful_tokens(value))) >= 2
        )

        # A user question containing only generic words or the product name is
        # not enough evidence to accept arbitrary high-frequency corpus records.
        if query and not query_candidates:
            return GroundedContext(items=())

        eligible = []
        for result in results:
            if (
                result.lexical_score < self.MIN_LEXICAL_RELEVANCE
                or result.score < self.MIN_RETRIEVAL_SCORE
            ):
                continue
            record = self.index.get_record(result.record_id)
            if record is None or not is_grounded_record(record.evidence, record.statement):
                continue
            eligible.append((result, record))

        # Compare candidates against the strongest match for this same query.
        # The lexical floor prevents a single generic word such as "evidence"
        # from grounding an otherwise unsupported question.
        best_ranked_score = max(
            (result.score for result, _ in eligible),
            default=0.0,
        )
        for result, record in eligible:
            if query_candidates and (
                best_ranked_score <= 0.0
                or result.score < best_ranked_score * self.MIN_RELATIVE_QUERY_RELEVANCE
            ):
                continue

            items.append(GroundedContextItem(
                record_id=record.record_id,
                concept_id=record.concept_id,
                statement=record.statement,
                score=result.score,
                provenance=record.provenance,
                evidence=record.evidence,
                aliases=record.aliases,
            ))
            if len(items) >= max_items:
                break
        return GroundedContext(items=tuple(items))
