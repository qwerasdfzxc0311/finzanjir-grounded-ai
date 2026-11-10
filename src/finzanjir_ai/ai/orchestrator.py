from __future__ import annotations

from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever
from finzanjir_ai.retrieval.rerank import Reranker
from finzanjir_ai.runtime.context import RuntimeContext


class GroundedAI:
    def __init__(self, index) -> None:
        self._retriever = HybridRetriever(index)
        self._reranker = Reranker(index)
        self._grounder = GroundedContextAssembler(index)
        self._generator = GroundedAnswerGenerator()

    def ask(self, query: str, *, runtime_refs: tuple[str, ...], working_memory_scope: str):
        context = RuntimeContext.from_refs(knowledge_refs=(), runtime_refs=runtime_refs, working_memory_scope=working_memory_scope)
        retrieved = self._retriever.search(query, top_k=8)
        reranked = self._reranker.rerank(query, retrieved)
        grounded = self._grounder.assemble(reranked)
        result = self._generator.generate(query, grounded)
        return type("AIIntegrationResult", (), {
            "answer": result.answer,
            "confidence": result.confidence,
            "abstained": result.abstained,
            "knowledge_refs": result.citations,
            "runtime_refs": context.runtime_refs,
            "citations": result.citations,
        })()
