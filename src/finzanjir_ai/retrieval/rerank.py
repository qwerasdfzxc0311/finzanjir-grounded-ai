from __future__ import annotations

from dataclasses import replace

from .hybrid import RetrievalResult
from .text import meaningful_tokens, tokenize
from finzanjir_ai.knowledge.index import KnowledgeIndex


_IDENTITY_QUERY_HINTS = (
    "FINZANJIR moliyaviy xavfsizlik firibgarlik zanjiri",
    "FINZANJIR maqsad vazifa himoya bank",
    "moliyaviy xavflarni aniqlash fuqarolar mablag'ini himoya qilish",
)

# Search hints only: the canonical author layer must supply every biographical fact.
_AUTHOR_QUERY_HINTS = (
    "Salamat Smaylov FINZANJIR muallifi yaratuvchisi asoschisi",
    "muallif tarjimai holi hayoti ta'lim qiziqishlari astronomiya kimyo",
    "FINZANJIR g'oyasi yaratilish sababi muallif motivatsiyasi",
)


class QueryExpander:
    """Local alias expansion that avoids firing on generic one-word overlaps."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def expand(self, query: str) -> tuple[str, ...]:
        original = query.strip()
        if not original:
            return ()

        expanded: list[str] = [original]
        raw_terms = set(tokenize(original))
        query_terms = set(meaningful_tokens(original))

        # A broad identity question has little lexical content after stopword
        # removal. Add search hints only; these are never treated as answer facts.
        if "finzanjir" in raw_terms and (
            len(query_terms) <= 1
            or bool(raw_terms & {"nima", "maqsad", "kerak", "loyiha", "qanday"})
        ):
            expanded.extend(_IDENTITY_QUERY_HINTS)

        author_terms = {
            "muallif", "muallifi", "yaratuvchi", "asoschi", "biografiya",
            "tarjimai", "hayoti", "qiziqishlari", "motivatsiya", "yaratgan",
            "salamat", "smaylov",
        }
        if raw_terms & author_terms:
            expanded.extend(_AUTHOR_QUERY_HINTS)

        alias_record_ids: dict[str, set[str]] = {}
        for record in self.index.records:
            for alias in record.aliases:
                for token in set(meaningful_tokens(alias)):
                    alias_record_ids.setdefault(token, set()).add(record.record_id)

        for record in self.index.records:
            for alias in record.aliases:
                alias_terms = set(meaningful_tokens(alias))
                if not alias_terms:
                    continue
                overlap = len(query_terms & alias_terms)
                exact_phrase = alias.casefold().strip() in original.casefold()
                unique_specific_term = (
                    len(query_terms) == 1
                    and "finzanjir" not in query_terms
                    and len(alias_record_ids.get(next(iter(query_terms)), set())) == 1
                    and bool(query_terms & alias_terms)
                )
                if exact_phrase or overlap >= 2 or unique_specific_term:
                    expanded.extend(record.aliases)
                    break

        return tuple(dict.fromkeys(term for term in expanded if term))


class Reranker:
    """Small, bounded alias-aware rerank bonus; no unbounded exact-match boost."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def rerank(self, query: str, results: tuple[RetrievalResult, ...]) -> tuple[RetrievalResult, ...]:
        normalized_query = " ".join(tokenize(query))
        query_terms = set(meaningful_tokens(query))
        scored = []
        for result in results:
            record = self.index.get_record(result.record_id)
            bonus = 0.0
            if record:
                for alias in record.aliases:
                    normalized_alias = " ".join(tokenize(alias))
                    alias_terms = set(meaningful_tokens(alias))
                    if normalized_alias and (
                        normalized_alias in normalized_query
                        or normalized_query in normalized_alias
                    ):
                        bonus = max(bonus, 0.20)
                    elif len(query_terms & alias_terms) >= 2 and alias_terms:
                        overlap = len(query_terms & alias_terms) / len(alias_terms)
                        bonus = max(bonus, min(0.12, 0.12 * overlap))
            scored.append(replace(result, score=min(1.0, result.score + bonus)))
        return tuple(sorted(scored, key=lambda item: (-item.score, item.record_id)))
