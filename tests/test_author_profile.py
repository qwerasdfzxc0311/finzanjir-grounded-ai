from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_author_profile_records
from finzanjir_ai.orchestration.engine import FINZANJIRAI


class FakeAuthorProvider:
    last_status = "ready"

    @staticmethod
    def can_send_text(_text):
        return True

    @staticmethod
    def expand_question(_question):
        return ()

    def generate_json(self, **kwargs):
        # The real generator validates cited IDs against retrieved evidence.
        return {
            "answer": "FINZANJIR loyihasining muallifi Salamat Smaylov.",
            "used_record_ids": ["author_0001"],
            "evidence_gaps": [],
        }


def test_author_profile_layer_has_only_author_confirmed_records():
    records = load_author_profile_records()
    assert len(records) >= 4
    assert all(item["evidence"]["verification"] == "author_confirmed" for item in records)
    assert any(item["id"] == "author_0001" for item in records)


def test_author_question_retrieves_author_profile_and_answers_from_it():
    index = build_knowledge_index(load_author_profile_records())
    ai = FINZANJIRAI(index)
    provider = FakeAuthorProvider()
    ai.language_model = provider
    ai.answer_generator.provider = provider

    result = ai.answer(
        "FINZANJIR muallifi kim?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )

    assert result.answer.abstained is False
    assert result.answer.generation_mode == "model"
    assert "author_0001" in result.answer.citations
    assert "Salamat Smaylov" in result.answer.answer


def test_author_profile_records_do_not_change_canonical_corpus_schema():
    records = load_author_profile_records()
    assert all(item["id"].startswith("author_") for item in records)


class OfflineAuthorProvider:
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


def _offline_author_ai():
    ai = FINZANJIRAI(build_knowledge_index(load_author_profile_records()))
    provider = OfflineAuthorProvider()
    ai.language_model = provider
    ai.answer_generator.provider = provider
    return ai


def test_author_identity_has_concise_fallback_when_provider_fails():
    result = _offline_author_ai().answer(
        "FINZANJIR muallifi kim?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "deterministic_fallback"
    assert result.answer.provider_status == "provider_failed"
    assert "Salamat Smaylov" in result.answer.answer
    assert result.answer.citations == ("author_0001",)


def test_author_motivation_has_concise_fallback_when_provider_fails():
    result = _offline_author_ai().answer(
        "Muallif nima uchun FINZANJIRni yaratgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "deterministic_fallback"
    assert "oilasi" in result.answer.answer.casefold()
    assert result.answer.citations == ("author_0004",)


def test_author_interests_have_concise_fallback_when_provider_fails():
    result = _offline_author_ai().answer(
        "Muallif nimalarga qiziqadi?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "deterministic_fallback"
    assert "astronomiya" in result.answer.answer.casefold()
    assert "kimyo" in result.answer.answer.casefold()
    assert result.answer.citations == ("author_0003",)


def test_author_birth_details_have_concise_fallback_when_provider_fails():
    result = _offline_author_ai().answer(
        "Muallif qachon va qayerda tug'ilgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "deterministic_fallback"
    assert "2003-yil 10-aprelda" in result.answer.answer
    assert "Qanliko'l" in result.answer.answer
    assert result.answer.citations == ("author_0002",)
