from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any

from finzanjir_ai.answer.generator import AnswerResult, GroundedAnswerGenerator
from finzanjir_ai.answer.providers import LLMGateway
from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.retrieval.cross_lingual import cross_lingual_query_variants
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextAssembler, GroundedContextItem
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker
from finzanjir_ai.retrieval.text import query_script_variants
from finzanjir_ai.runtime.context import RuntimeContext
from finzanjir_ai.memory.conversation import build_conversation_context
from finzanjir_ai.orchestration.intent import classify_query_intent, is_author_overview_query


def _is_author_layer_record(record: Any) -> bool:
    """Identify author biography/motivation evidence by metadata, not ID prefix alone."""
    if record is None:
        return False
    if record.record_id.startswith("author_"):
        return True
    if record.entity_id == "person:salamat_smaylov":
        return True
    if (record.facet or "").casefold() in {
        "identity", "birth_details", "interests", "project_motivation",
        "author_biography", "author_profile",
    }:
        return True

    author_section_markers = (
        "muallif profili",
        "muallifning motivatsiyasi",
        "loyiha muallifining motivatsiyasi",
        "loyiha muallifining qarashi",
        "muallifning qarashi",
        "author profile",
        "author biography",
        "author motivation",
    )
    for source in record.provenance:
        if not isinstance(source, dict):
            continue
        if source.get("source_type") == "author_provided_profile":
            return True
        sections = str(source.get("source_sections") or source.get("sections") or "").casefold()
        if any(marker in sections for marker in author_section_markers):
            return True

    aliases = " ".join(record.aliases).casefold()
    if any(marker in aliases for marker in (
        "muallifning kelajak haqidagi qarashi",
        "muallif tarjimai holi",
        "muallif motivatsiyasi",
        "muallifning shaxsiy",
        "muallifning qiziqishlari",
        "muallif bolaligida",
        "author profile",
        "author biography",
    )):
        return True

    statement = record.statement.casefold()
    if any(marker in statement for marker in (
        "muallif rasmi", "muallif profili", "muallifning tarjimai holi",
    )):
        return True
    return False


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
        conversation_history: tuple[dict[str, str], ...] = (),
        top_k: int = 8,
    ) -> OrchestrationResult:
        conversation = build_conversation_context(query, conversation_history)
        contextual_query = conversation.contextual_query

        # Clear general-knowledge questions must not be rejected merely because
        # the closed FINZANJIR project corpus contains no answer for them.
        query_intent = classify_query_intent(contextual_query)
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
            answer = self.answer_generator.generate_general_knowledge(query, conversation_context=conversation.context_text)
            return OrchestrationResult(
                answer=answer,
                grounded_context=GroundedContext(items=()),
                runtime_context=runtime,
            )

        # A broad "tell me about this person" request is an entity lookup,
        # not a keyword-match task. Resolve the canonical entity first, then let
        # the answer composer select and organize its verified biography facets.
        if query_intent == "author" and is_author_overview_query(contextual_query):
            profile = self.grounder.assemble_entity("person:salamat_smaylov", max_items=top_k)
            if profile.items:
                runtime = RuntimeContext.from_refs(
                    knowledge_refs=tuple(item.record_id for item in profile.items),
                    runtime_refs=runtime_refs,
                    working_memory_scope=working_memory_scope,
                )
                answer = self.answer_generator.generate(query, profile, context_query=contextual_query, conversation_context=conversation.context_text)
                return OrchestrationResult(
                    answer=answer,
                    grounded_context=profile,
                    runtime_context=runtime,
                )

        if query_intent == "project_overview":
            record = self.index.get_record("project_0001")
            items = ()
            if record is not None:
                items = (GroundedContextItem(
                    record_id=record.record_id,
                    concept_id=record.concept_id,
                    statement=record.statement,
                    score=1.0,
                    provenance=record.provenance,
                    evidence=record.evidence,
                    aliases=record.aliases,
                ),)
            overview_context = GroundedContext(items=items)
            runtime = RuntimeContext.from_refs(
                knowledge_refs=tuple(item.record_id for item in items),
                runtime_refs=runtime_refs,
                working_memory_scope=working_memory_scope,
            )
            answer = self.answer_generator.generate(query, overview_context, context_query=contextual_query, conversation_context=conversation.context_text)
            return OrchestrationResult(
                answer=answer,
                grounded_context=overview_context,
                runtime_context=runtime,
            )

        # Multi-query retrieval: the original question has the highest weight;
        # local alias rewrites and model-proposed rewrites expand recall only.
        # Reciprocal-rank fusion combines candidate lists without pretending
        # that a rewrite itself is evidence. The final reranker still sees the
        # user's original question.
        model_queries = self.language_model.expand_question(contextual_query)
        local_queries = self.expander.expand(contextual_query)
        query_specs = [(contextual_query, 2.0)]
        # Central-Asian Cyrillic/Latin spellings and cross-lingual domain terms
        # can refer to the same concepts. These are lower-weight search hints,
        # never evidence; the original query remains highest-weight and is used
        # by the final reranker.
        script_queries = query_script_variants(contextual_query)
        query_specs.extend((value, 0.9) for value in script_queries[1:])
        cross_lingual_queries = cross_lingual_query_variants(contextual_query)
        query_specs.extend(
            (value, 0.65) for value in cross_lingual_queries[len(script_queries):]
        )
        query_specs.extend((value, 1.0) for value in local_queries if value.strip() != contextual_query.strip())
        query_specs.extend((value, 0.7) for value in model_queries if value.strip())
        deduplicated = []
        seen_queries = set()
        for value, weight in query_specs:
            key = value.casefold().strip()
            if key and key not in seen_queries:
                seen_queries.add(key)
                deduplicated.append((value, weight))

        fused = {}
        total_weight = sum(weight for _, weight in deduplicated) or 1.0
        candidate_limit = max(top_k * 4, 24)
        for search_query, weight in deduplicated:
            results = self.retriever.search(search_query, top_k=candidate_limit)
            for rank, result in enumerate(results, start=1):
                entry = fused.setdefault(result.record_id, {
                    "rrf": 0.0,
                    "lexical": 0.0,
                    "best_score": 0.0,
                })
                entry["rrf"] += weight / (60.0 + rank)
                entry["lexical"] = max(entry["lexical"], result.lexical_score)
                entry["best_score"] = max(entry["best_score"], result.score)

        merged = []
        for record_id, values in fused.items():
            normalized_rrf = min(1.0, values["rrf"] * 61.0 / total_weight)
            combined_score = min(
                1.0,
                0.70 * values["lexical"] + 0.30 * normalized_rrf,
            )
            merged.append(RetrievalResult(
                record_id=record_id,
                score=combined_score,
                lexical_score=values["lexical"],
                semantic_score=0.0,
            ))
        merged.sort(key=lambda item: (-item.score, item.record_id))
        ranked = self.reranker.rerank(contextual_query, tuple(merged))
        if query_intent == "author":
            # Author questions use the separately confirmed biography layer only.
            ranked = tuple(
                item for item in ranked
                if _is_author_layer_record(self.index.get_record(item.record_id))
            )
        else:
            # Legacy V14/ZIP records may carry author material under ck_/src3_
            # IDs. Isolate by entity, facet and provenance as well as ID.
            ranked = tuple(
                item for item in ranked
                if not _is_author_layer_record(self.index.get_record(item.record_id))
            )
        grounded = self.grounder.assemble(
            ranked,
            query=contextual_query,
            query_alternatives=tuple(value for value, _ in deduplicated[1:]),
            max_items=top_k,
        )
        runtime = RuntimeContext.from_refs(
            knowledge_refs=tuple(item.record_id for item in grounded.items),
            runtime_refs=runtime_refs,
            working_memory_scope=working_memory_scope,
        )
        answer = self.answer_generator.generate(query, grounded, context_query=contextual_query, conversation_context=conversation.context_text)
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
