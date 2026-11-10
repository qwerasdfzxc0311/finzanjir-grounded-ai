from __future__ import annotations

from dataclasses import dataclass
import re

from finzanjir_ai.knowledge.index import KnowledgeIndex

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class RetrievalResult:
    record_id: str
    score: float
    lexical_score: float
    semantic_score: float


class HybridRetriever:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def search(self, query: str, *, top_k: int = 10) -> tuple[RetrievalResult, ...]:
        if top_k <= 0:
            return ()
        query_tokens = {token.casefold() for token in _TOKEN_RE.findall(query)}
        if not query_tokens:
            return ()

        results: list[RetrievalResult] = []
        for record in self.index.records:
            text_tokens = {token.casefold() for token in _TOKEN_RE.findall(record.searchable_text)}
            overlap = len(query_tokens & text_tokens)
            lexical = overlap / len(query_tokens)
            semantic = overlap / len(query_tokens | text_tokens) if text_tokens else 0.0
            score = 0.7 * lexical + 0.3 * semantic
            if score > 0:
                results.append(RetrievalResult(record.record_id, score, lexical, semantic))

        results.sort(key=lambda item: (-item.score, item.record_id))
        return tuple(results[:top_k])
