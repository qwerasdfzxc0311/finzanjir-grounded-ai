from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math

from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.language.morphology import morphological_stem
from finzanjir_ai.language.normalization import character_ngrams
from .text import meaningful_tokens


@dataclass(frozen=True)
class RetrievalResult:
    record_id: str
    score: float
    lexical_score: float
    semantic_score: float


class HybridRetriever:
    """Deterministic IDF/BM25-style lexical retrieval.

    Alias terms receive extra weight, while document-length normalization reduces
    the advantage previously given to very long narrative records. This remains
    lexical retrieval; semantic embeddings are a separately evaluated future stage.
    """

    K1 = 1.2
    B = 0.75

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index
        self._term_frequencies: tuple[Counter[str], ...] = tuple(
            self._record_frequencies(record.statement, record.aliases)
            for record in index.records
        )
        self._document_lengths = tuple(
            sum(frequencies.values()) for frequencies in self._term_frequencies
        )
        self._average_length = (
            sum(self._document_lengths) / len(self._document_lengths)
            if self._document_lengths else 1.0
        ) or 1.0
        document_frequency: Counter[str] = Counter()
        for frequencies in self._term_frequencies:
            document_frequency.update(frequencies.keys())
        count = max(1, len(self._term_frequencies))
        self._idf = {
            term: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }
        self._vocabulary_ngrams = {
            term: frozenset(character_ngrams(term, min_n=2, max_n=4))
            for term in self._idf
            if len(term) >= 5
        }
        ngram_terms: dict[str, list[str]] = defaultdict(list)
        for term, grams in self._vocabulary_ngrams.items():
            for gram in grams:
                ngram_terms[gram].append(term)
        self._ngram_to_terms = {
            gram: tuple(sorted(terms))
            for gram, terms in ngram_terms.items()
        }

    @staticmethod
    def _record_frequencies(statement: str, aliases: tuple[str, ...]) -> Counter[str]:
        frequencies: Counter[str] = Counter(
            morphological_stem(token) for token in meaningful_tokens(statement)
        )
        for alias in aliases:
            for token in meaningful_tokens(alias):
                frequencies[morphological_stem(token)] += 2
        return frequencies

    def _resolve_typo(self, term: str) -> str:
        """Resolve a clear single-token typo using character n-gram overlap.

        This is typo-tolerant lexical matching, not semantic similarity.
        """
        if term in self._idf or len(term) < 5 or not self._vocabulary_ngrams:
            return term
        grams = set(character_ngrams(term, min_n=2, max_n=4))
        candidates: set[str] = set()
        for gram in grams:
            candidates.update(self._ngram_to_terms.get(gram, ()))
        if len(candidates) > 4000:
            candidates = {
                candidate
                for gram in grams if len(gram.strip()) >= 3
                for candidate in self._ngram_to_terms.get(gram, ())
            }
        best_term = term
        best_score = 0.0
        best_overlap = 0.0
        for candidate in sorted(candidates):
            candidate_grams = self._vocabulary_ngrams[candidate]
            if abs(len(candidate) - len(term)) > 2:
                continue
            intersection = len(grams & candidate_grams)
            if not intersection:
                continue
            union = len(grams | candidate_grams)
            jaccard = intersection / union
            overlap = intersection / min(len(grams), len(candidate_grams))
            if (jaccard, overlap, candidate) > (best_score, best_overlap, best_term):
                best_term, best_score, best_overlap = candidate, jaccard, overlap
        if best_score >= 0.60 and best_overlap >= 0.80:
            return best_term
        return term

    def search(self, query: str, *, top_k: int = 10) -> tuple[RetrievalResult, ...]:
        if top_k <= 0:
            return ()
        raw_terms = tuple(dict.fromkeys(
            morphological_stem(token) for token in meaningful_tokens(query)
        ))
        if not raw_terms:
            return ()
        query_terms = tuple(dict.fromkeys(self._resolve_typo(term) for term in raw_terms))

        query_weight = sum(self._idf.get(term, 0.0) for term in query_terms)
        if query_weight <= 0:
            return ()

        results: list[RetrievalResult] = []
        for record, frequencies, length in zip(
            self.index.records, self._term_frequencies, self._document_lengths
        ):
            matched_weight = 0.0
            bm25 = 0.0
            for term in query_terms:
                term_idf = self._idf.get(term, 0.0)
                term_frequency = frequencies.get(term, 0)
                if not term_frequency or not term_idf:
                    continue
                matched_weight += term_idf
                denominator = term_frequency + self.K1 * (
                    1.0 - self.B + self.B * length / self._average_length
                )
                bm25 += term_idf * (
                    term_frequency * (self.K1 + 1.0) / denominator
                )

            if matched_weight <= 0:
                continue
            lexical = matched_weight / query_weight
            bm25_normalized = bm25 / (query_weight * (self.K1 + 1.0))
            score = 0.75 * lexical + 0.25 * min(1.0, bm25_normalized)
            results.append(
                RetrievalResult(
                    record_id=record.record_id,
                    score=min(1.0, score),
                    lexical_score=min(1.0, lexical),
                    semantic_score=0.0,
                )
            )

        results.sort(key=lambda item: (-item.score, item.record_id))
        return tuple(results[:top_k])
