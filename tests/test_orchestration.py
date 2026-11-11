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
