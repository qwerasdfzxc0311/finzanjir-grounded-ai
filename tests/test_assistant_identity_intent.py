from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.orchestration.intent import classify_query_intent


def test_assistant_identity_phrases_route_separately():
    assert classify_query_intent("Sening maqsading nima?") == "assistant_identity"
    assert classify_query_intent("Sen kimsan?") == "assistant_identity"
    assert classify_query_intent("Sening vazifang nima?") == "assistant_identity"


def test_assistant_identity_answers_without_model_or_project_documents():
    ai = FINZANJIRAI(build_knowledge_index([]))
    result = ai.answer(
        "Sening maqsading nima?",
        runtime_refs=(),
        working_memory_scope="identity-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "assistant_identity"
    assert result.answer.provider_status == "not_attempted"
    assert result.answer.citations == ()
    assert "sun'iy intellekt yordamchisiman" in result.answer.answer
    assert "hisobini bloklamayman" in result.answer.answer
