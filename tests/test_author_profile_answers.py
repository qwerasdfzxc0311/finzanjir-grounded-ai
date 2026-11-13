from finzanjir_ai.knowledge.index import build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.engine import FINZANJIRAI


class OfflineProvider:
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


def _offline_ai():
    ai = FINZANJIRAI(build_index_from_document(load_canonical_knowledge()))
    provider = OfflineProvider()
    ai.language_model = provider
    ai.answer_generator.provider = provider
    return ai


def test_author_identity_answers_from_separate_profile_when_provider_fails():
    result = _offline_ai().answer(
        "FINZANJIR muallifi kim?",
        runtime_refs=(),
        working_memory_scope="author",
    )
    assert result.answer.abstained is False
    assert "Smaylov Salamat Tangrbergen uli" in result.answer.answer
    assert "author_profile_0001" in result.answer.citations


def test_author_motivation_answers_from_grounded_profile_when_provider_fails():
    result = _offline_ai().answer(
        "Muallif nima uchun FINZANJIRni yaratgan?",
        runtime_refs=(),
        working_memory_scope="author",
    )
    assert result.answer.abstained is False
    assert "moliyaviy" in result.answer.answer.casefold()
    assert "author_profile_0003" in result.answer.citations


def test_author_interests_answer_from_user_provided_profile_when_provider_fails():
    result = _offline_ai().answer(
        "Muallif nimalarga qiziqadi?",
        runtime_refs=(),
        working_memory_scope="author",
    )
    assert result.answer.abstained is False
    assert "astronomiya" in result.answer.answer.casefold()
    assert "kimyo" in result.answer.answer.casefold()
    assert "author_profile_0002" in result.answer.citations
