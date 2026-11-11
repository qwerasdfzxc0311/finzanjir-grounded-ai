from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from finzanjir_ai.knowledge.index import KnowledgeIndex
from .hybrid import RetrievalResult


GROUNDED_EVIDENCE_STATUSES = frozenset({
    "established",
    "project_source",
    "source_derived",
    "supported",
})

# Common function words are poor evidence of semantic relevance. Keeping this
# list small avoids turning the lexical guard into a language model while
# preventing queries such as "unsupported fact with no grounded evidence" from
# matching merely because they contain the generic word "evidence".
_QUERY_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "does", "for", "from", "how",
    "in", "is", "it", "no", "of", "on", "or", "the", "to", "what", "why",
    "with", "without",
    "bu", "bilan", "bir", "bo", "bo'yicha", "deb", "degan", "ekan", "uchun",
    "va", "yoki", "qanday", "nima", "nega", "ning", "dan", "da", "ga",
})


UNVERIFIED_STATUS_MARKERS = (
    "tasdiqlanmagan",
    "unverified",
    "proposal",
    "taklif",
    "ochiq masala",
)


def is_grounded_evidence(evidence: Any) -> bool:
    return (
        isinstance(evidence, dict)
        and evidence.get("status") in GROUNDED_EVIDENCE_STATUSES
    )


def is_grounded_record(evidence: Any, statement: str) -> bool:
    if not is_grounded_evidence(evidence):
        return False
    normalized = str(statement).casefold()
    return not any(marker in normalized for marker in UNVERIFIED_STATUS_MARKERS)


def _query_tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[^\W_]+", value, flags=re.UNICODE)
        if token.casefold() not in _QUERY_STOPWORDS
    }


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
    MIN_LEXICAL_RELEVANCE = 0.35
    MIN_QUERY_RELEVANCE = 0.60

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def assemble(
        self,
        results: tuple[RetrievalResult, ...],
        *,
        query: str | None = None,
        max_items: int = 8,
    ) -> GroundedContext:
        items = []
        query_tokens = _query_tokens(query) if query else set()
        for result in results:
            if (
                result.lexical_score < self.MIN_LEXICAL_RELEVANCE
                or result.score < self.MIN_RETRIEVAL_SCORE
            ):
                continue
            record = self.index.get_record(result.record_id)
            if record is None or not is_grounded_evidence(record.evidence):
                continue

            if query_tokens:
                record_tokens = _query_tokens(record.statement + " " + " ".join(record.aliases))
                overlap = len(query_tokens & record_tokens)
                relevance = overlap / len(query_tokens)
                if relevance < self.MIN_QUERY_RELEVANCE:
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
