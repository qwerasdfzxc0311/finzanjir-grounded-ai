from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.orchestration.intent import (
    classify_query_intent,
    is_author_critique_query,
    is_project_overview_query,
    is_system_complement_query,
)
from finzanjir_ai.prototype.flow import build_system_flow


class UnavailableProvider:
    last_status = "provider_failed"

    @staticmethod
    def can_send_text(_text):
        return True

    @staticmethod
    def expand_question(_question):
        return ()

    @staticmethod
    def generate_json(**_kwargs):
        return None


def _engine():
    engine = FINZANJIRAI(build_system_flow().demo_knowledge_index())
    provider = UnavailableProvider()
    engine.language_model = provider
    engine.answer_generator.provider = provider
    return engine


def test_broad_overview_with_why_needed_phrase_keeps_overview_intent():
    query = "FINZANJIR nima va nima uchun kerak?"
    assert is_project_overview_query(query)
    assert classify_query_intent(query) == "project_overview"

    result = _engine().answer(query, runtime_refs=(), working_memory_scope="semantic-regression")
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "project_overview_localized"
    assert result.answer.citations == ("project_0001",)
    assert "moliyaviy firibgarlik" in result.answer.answer
    assert "hovlidagi ekin" not in result.answer.answer


def test_replace_vs_complement_question_gets_direct_concise_answer():
    query = "FINZANJIR mavjud bank xavfsizlik tizimlarini almashtiradimi yoki to'ldiradimi?"
    assert is_system_complement_query(query)

    result = _engine().answer(query, runtime_refs=(), working_memory_scope="semantic-regression")
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "system_complement_localized"
    assert result.answer.citations == ("project_0010",)
    assert "to'ldirish" in result.answer.answer
    assert "avtomatik bloklash buyrug'i emas" in result.answer.answer


def test_author_overpraise_question_is_an_evidence_based_critique_not_biography():
    query = "Muallif FINZANJIRni ortiqcha maqtayaptimi?"
    assert is_author_critique_query(query)
    assert classify_query_intent(query) == "author"

    result = _engine().answer(query, runtime_refs=(), working_memory_scope="semantic-regression")
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_claims_critique_grounded"
    assert "author_0008" in result.answer.citations
    assert "maqsad va kelajak haqidagi qarashlar" in result.answer.answer
    assert "mustaqil texnik audit" in result.answer.answer
    assert "hayotiy tajribalari sababli" not in result.answer.answer
