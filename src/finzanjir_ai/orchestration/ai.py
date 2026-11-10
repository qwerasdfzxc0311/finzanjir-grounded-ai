from __future__ import annotations

from dataclasses import dataclass

from finzanjir_ai.answer.generator import AnswerResult, GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever
from finzanjir_ai.retrieval.rerank import Reranker
from finzanjir_ai.runtime.context import RuntimeContext


@dataclass(frozen=True)
class OrchestratedAnswer:
    answer: str
    confidence: float
    abstained: bool
    citations: tuple[str, ...]
    runtime_refs: tuple[str, ...]


class GroundedAI:
    def __init__(self, retriever: HybridRetriever, reranker: Reranker, grounder: GroundedContextAssembler, generator: GroundedAnswerGenerator) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.grounder = grounder
        self.generator = generator

    def answer(self, query: str, runtime_context: RuntimeContext) -> OrchestratedAnswer:
        retrieved = self.retriever.search(query, top_k=8)
        reranked = self.reranker.rerank(query, retrieved)
        grounded = self.grounder.assemble(reranked)
        generated: AnswerResult = self.generator.generate(query, grounded)
        return OrchestratedAnswer(
            answer=generated.answer,
            confidence=generated.confidence,
            abstained=generated.abstained,
            citations=generated.citations,
            runtime_refs=runtime_context.runtime_refs,
        )
