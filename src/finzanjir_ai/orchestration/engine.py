from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock

from finzanjir_ai.answer.generator import AnswerResult, GroundedAnswerGenerator
from finzanjir_ai.answer.providers import LLMGateway
from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker
from finzanjir_ai.runtime.context import RuntimeContext
from finzanjir_ai.orchestration.intent import classify_query_intent


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
        # Clear general-knowledge questions must not be rejected merely because
        # the closed FINZANJIR project corpus contains no answer for them.
        query_intent = classify_query_intent(query)
        if query_intent == "assistant_identity":
            runtime = RuntimeContext.from_refs(
                knowledge_refs=(),
                runtime_refs=runtime_refs,
                working_memory_scope=working_memory_scope,
            )
            answer = AnswerResult(
                answer=(
                    "Men FINZANJIR loyihasiga xizmat qiluvchi sun'iy intellekt yordamchisiman. "
                    "Mening vazifam loyiha hujjatlari va tasdiqlangan bilimlar asosida savollarga "
                    "tushunarli javob berish, FINZANJIR imkoniyatlari va cheklovlarini izohlash "
                    "hamda umumiy savollarni loyiha savollaridan ajratishdir. "
                    "Men bank qarorini qabul qilmayman, fuqaroning hisobini bloklamayman va "
                    "huquqiy vakolatli organ o'rnini bosmayman. Dalil yetarli bo'lmasa, buni ochiq aytaman."
                ),
                confidence=1.0,
                abstained=False,
                citations=(),
                generation_mode="assistant_identity",
                provider_status="not_attempted",
            )
            return OrchestrationResult(
                answer=answer,
                grounded_context=GroundedContext(items=()),
                runtime_context=runtime,
            )

        if query_intent == "general_knowledge":
            runtime = RuntimeContext.from_refs(
                knowledge_refs=(),
                runtime_refs=runtime_refs,
                working_memory_scope=working_memory_scope,
            )
            answer = self.answer_generator.generate_general_knowledge(query)
            return OrchestrationResult(
                answer=answer,
                grounded_context=GroundedContext(items=()),
                runtime_context=runtime,
            )

        # Retrieve candidate evidence from the user's actual question first.
        # Rewritten/expanded queries may add hints in a later stage, but their
        # scores must never replace direct-query relevance: doing so allowed
        # loosely related records to answer unsupported questions.
        model_queries = self.language_model.expand_question(query)
        local_queries = self.expander.expand(query)
        direct_results = self.retriever.search(query, top_k=top_k)
        ranked = self.reranker.rerank(query, direct_results)
        if query_intent == "author":
            # Author questions use the separately confirmed biography layer only.
            # Similar names in project documents are not sufficient biographical evidence.
            ranked = tuple(item for item in ranked if item.record_id.startswith("author_"))
        grounded = self.grounder.assemble(
            ranked,
            query=query,
            query_alternatives=tuple(dict.fromkeys((*model_queries, *local_queries))),
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


_ENGINE_CACHE: OrderedDict[int, tuple[KnowledgeIndex, FINZANJIRAI]] = OrderedDict()
_ENGINE_CACHE_LOCK = RLock()
_ENGINE_CACHE_MAXSIZE = 4


def get_finzanjir_ai(index: KnowledgeIndex) -> FINZANJIRAI:
    """Reuse the precomputed retrieval statistics for the same corpus index."""
    key = id(index)
    with _ENGINE_CACHE_LOCK:
        cached = _ENGINE_CACHE.get(key)
        if cached is not None and cached[0] is index:
            _ENGINE_CACHE.move_to_end(key)
            return cached[1]
        engine = FINZANJIRAI(index)
        _ENGINE_CACHE[key] = (index, engine)
        _ENGINE_CACHE.move_to_end(key)
        while len(_ENGINE_CACHE) > _ENGINE_CACHE_MAXSIZE:
            _ENGINE_CACHE.popitem(last=False)
        return engine
