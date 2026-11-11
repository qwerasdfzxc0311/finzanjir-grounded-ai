from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.prototype.flow import build_system_flow


def test_orchestrator_abstains_when_retrieval_is_only_weakly_relevant():
    index = build_system_flow().demo_knowledge_index()

    result = FINZANJIRAI(index).answer(
        "Unsupported fact with no grounded evidence",
        runtime_refs=(),
        working_memory_scope="test",
    )

    assert result.answer.abstained is True
    assert result.answer.confidence < 0.35
    assert result.answer.citations == ()


def test_orchestrator_keeps_strongly_relevant_grounding():
    index = build_system_flow().demo_knowledge_index()

    result = FINZANJIRAI(index).answer(
        "Why does case escalation require evidence?",
        runtime_refs=(),
        working_memory_scope="test",
    )

    assert result.answer.abstained is False
    assert result.answer.confidence >= 0.35
    assert result.answer.citations
