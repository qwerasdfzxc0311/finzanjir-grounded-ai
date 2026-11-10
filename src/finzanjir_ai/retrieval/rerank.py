from __future__ import annotations

from dataclasses import replace

from .hybrid import RetrievalResult
from finzanjir_ai.knowledge.index import KnowledgeIndex


class QueryExpander:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def expand(self, query: str) -> tuple[str, ...]:
        terms = {query.strip()} if query.strip() else set()
        query_tokens = {token.casefold() for token in query.split()}
        for record in self.index.records:
            if query_tokens & {alias.casefold() for alias in record.aliases for _ in [0]}:
                terms.update(record.aliases)
            elif any(token in alias.casefold().split() for token in query_tokens for alias in record.aliases):
                terms.update(record.aliases)
        return tuple(sorted(term for term in terms if term))


class Reranker:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def rerank(self, query: str, results: tuple[RetrievalResult, ...]) -> tuple[RetrievalResult, ...]:
        q = query.casefold().strip()
        scored = []
        for result in results:
            record = self.index.get_record(result.record_id)
            bonus = 0.0
            if record and any(alias.casefold() == q or q in alias.casefold() for alias in record.aliases):
                bonus = 1.0
            scored.append(replace(result, score=result.score + bonus))
        return tuple(sorted(scored, key=lambda item: (-item.score, item.record_id)))
