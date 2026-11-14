from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI


def test_ai_orchestrator_connects_retrieval_grounding_runtime_and_answer():
    index = build_knowledge_index(
        [
            {
                "id": "ck-1",
                "concept_id": "c1",
                "canonical_concept_id": "c1",
                "statement": "Fraud signal requires supporting evidence.",
                "aliases": ["suspicious signal"],
                "evidence": {"status": "supported"},
                "provenance": [{"source": "source-a"}],
                "reconciliation": {},
            }
        ]
    )
    ai = FINZANJIRAI(index)

    result = ai.answer(
        "Why does fraud signal require supporting evidence?",
        runtime_refs=("tx-1", "sig-1"),
        working_memory_scope="case-1",
    )

    assert result.answer.abstained is False
    assert result.answer.citations == ("ck-1",)
    assert result.runtime_context.runtime_refs == ("tx-1", "sig-1")
    assert result.runtime_context.can_write_authoritative_knowledge is False


def test_ai_orchestrator_abstains_when_nothing_is_grounded():
    index = build_knowledge_index([])
    result = FINZANJIRAI(index).answer(
        "Unknown question",
        runtime_refs=(),
        working_memory_scope="case-2",
    )
    assert result.answer.abstained is True


def test_runtime_cross_lingual_hint_retrieves_only_grounded_internal_evidence():
    index = build_knowledge_index(
        [
            {
                "id": "verified-financial-protection",
                "concept_id": "financial-protection",
                "statement": (
                    "FINZANJIR moliyaviy firibgarlikdan himoya qilish uchun "
                    "banklararo tizimda shubhali signal va ma'lumot almashuvini "
                    "tahlil qilishga qaratilgan loyiha."
                ),
                "aliases": [
                    "moliyaviy firibgarlik himoya fuqaro banklararo tizim",
                    "shubhali signal ma'lumot almashuv",
                ],
                "evidence": {"status": "supported", "verification": "verified"},
                "provenance": [{"source": "synthetic-test-fixture"}],
                "reconciliation": {},
            },
            {
                "id": "unverified-external-comparison",
                "concept_id": "external-system",
                "statement": (
                    "An unrelated foreign system uses a different architecture "
                    "and has no verified relationship to FINZANJIR."
                ),
                "aliases": ["foreign system architecture"],
                "evidence": {"status": "unconfirmed", "verification": "unverified"},
                "provenance": [{"source": "synthetic-test-fixture"}],
                "reconciliation": {},
            },
        ]
    )
    ai = FINZANJIRAI(index)
    # Force a fully offline test: no Gemini/OpenRouter query expansion or generation.
    ai.language_model.expand_question = lambda _query: ()
    ai.answer_generator.language_model.generate_json = lambda **_kwargs: None

    result = ai.answer(
        "Чем FINZANJIR отличается от похожих систем для защиты граждан от финансового мошенничества?",
        runtime_refs=(),
        working_memory_scope="synthetic-test",
    )

    grounded_ids = {item.record_id for item in result.grounded_context.items}
    assert "verified-financial-protection" in grounded_ids
    assert "unverified-external-comparison" not in grounded_ids
    assert result.runtime_context.knowledge_refs == tuple(
        item.record_id for item in result.grounded_context.items
    )
    assert all(
        item.evidence.get("verification") != "unverified"
        for item in result.grounded_context.items
    )
