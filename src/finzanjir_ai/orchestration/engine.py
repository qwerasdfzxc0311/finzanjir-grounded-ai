from __future__ import annotations

from dataclasses import dataclass

from finzanjir_ai.answer.generator import AnswerResult, GroundedAnswerGenerator
from finzanjir_ai.answer.providers import LLMGateway
from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker
from finzanjir_ai.runtime.context import RuntimeContext


@dataclass(frozen=True)
class OrchestrationResult:
    answer: AnswerResult
    grounded_context: GroundedContext
    runtime_context: RuntimeContext


class FINZANJIRAI:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index
        self.retriever = HybridRetriever(index)
        self.expander = QueryExpander(index)
        self.reranker = Reranker(index)
        self.grounder = GroundedContextAssembler(index)
        self.language_model = LLMGateway()
        self.answer_generator = GroundedAnswerGenerator(self.language_model)

    def answer(
        self,
        query: str,
        *,
        runtime_refs: tuple[str, ...],
        working_memory_scope: str,
        top_k: int = 8,
    ) -> OrchestrationResult:
        # The model may rewrite/expand a difficult question, but it never supplies
        # facts. Every candidate must still be retrieved from the canonical corpus.
        model_queries = self.language_model.expand_question(query)
        local_queries = self.expander.expand(query)
        queries = tuple(dict.fromkeys((query, *model_queries, *local_queries)))

        by_id: dict[str, RetrievalResult] = {}
        for expanded in queries:
            for result in self.retriever.search(expanded, top_k=top_k):
                current = by_id.get(result.record_id)
                if current is None or result.score > current.score:
                    by_id[result.record_id] = result

        ranked = self.reranker.rerank(query, tuple(by_id.values()))
        grounded = self.grounder.assemble(
            ranked,
            query=query,
            query_alternatives=model_queries + local_queries,
            max_items=top_k,
        )
        runtime = RuntimeContext.from_refs(
            knowledge_refs=tuple(item.record_id for item in grounded.items),
            runtime_refs=runtime_refs,
            working_memory_scope=working_memory_scope,
        )
        answer = self.answer_generator.generate(query, grounded)
        return OrchestrationResult(
            answer=answer,
            grounded_context=grounded,
            runtime_context=runtime,
        )
