from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI


class FakeGeneralProvider:
    last_status = "ready"

    @staticmethod
    def can_send_text(_text):
        return True

    def generate_json(self, **_kwargs):
        return {"answer": "Toshbaqalar turi va yashash sharoitiga qarab turlicha umr ko'radi."}


def test_general_knowledge_question_bypasses_empty_project_corpus():
    ai = FINZANJIRAI(build_knowledge_index([]))
    ai.language_model = FakeGeneralProvider()
    ai.answer_generator.provider = ai.language_model

    result = ai.answer(
        "toshvaqa qansha yil umir koradi",
        runtime_refs=(),
        working_memory_scope="general",
    )

    assert result.answer.abstained is False
    assert result.answer.generation_mode == "general_knowledge_model"
    assert result.answer.citations == ()
    assert "Toshbaqalar" in result.answer.answer


def test_project_question_still_abstains_without_project_evidence():
    result = FINZANJIRAI(build_knowledge_index([])).answer(
        "FINZANJIR nima?",
        runtime_refs=(),
        working_memory_scope="project",
    )
    assert result.answer.abstained is True
    assert result.answer.generation_mode == "no_grounded_evidence"
