import pytest

from finzanjir_ai.answer.generator import AnswerResult
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI


@pytest.mark.parametrize(
    "query",
    [
        "Какова цель FINZANJIR в защите граждан от финансового мошенничества?",
        "What is FINZANJIR's purpose in financial fraud protection?",
        "FINZANJIR-дің мақсаты қандай және қаржылық алаяқтықтан қорғау?",
        "FINZANJIR maqseti qanday, finanslıq firibgarlikten qorǵaw?",
    ],
)
def test_runtime_retrieval_uses_keyless_cross_lingual_hint(query):
    index = build_knowledge_index([
        {
            "id": "ck-project-purpose",
            "concept_id": "project:finzanjir:purpose",
            "canonical_concept_id": "project:finzanjir:purpose",
            "statement": (
                "FINZANJIRning maqsadi — moliyaviy firibgarlik xavfini erta aniqlash, "
                "fuqarolarning qonuniy mablag'lari va tranzaksiyalarini himoya qilishga ko'maklashish."
            ),
            "aliases": ["FINZANJIR moliyaviy xavfsizlik platformasi"],
            "evidence": {
                "status": "source_derived",
                "sources": [{"source_id": "project-doc", "section": "Project purpose"}],
            },
            "provenance": [{"source": "synthetic-test-fixture"}],
            "reconciliation": {},
        }
    ])
    ai = FINZANJIRAI(index)
    # Keep the test fully offline: no provider-generated rewrites or answer call.
    ai.language_model.expand_question = lambda _query: ()
    ai.answer_generator.generate = lambda _query, context, **_kwargs: AnswerResult(
        answer="grounded test answer",
        confidence=1.0,
        abstained=False,
        citations=tuple(item.record_id for item in context.items),
    )

    result = ai.answer(
        query,
        runtime_refs=(),
        working_memory_scope="synthetic-test",
    )

    assert result.answer.abstained is False
    assert "ck-project-purpose" in result.answer.citations
    assert "ck-project-purpose" in tuple(item.record_id for item in result.grounded_context.items)
