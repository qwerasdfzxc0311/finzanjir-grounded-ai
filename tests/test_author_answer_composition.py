from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_author_profile_records
from finzanjir_ai.orchestration.engine import FINZANJIRAI


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


def _engine_with_author_profile():
    records = load_author_profile_records()
    # Deliberately add a second-language duplicate to verify that author mode
    # uses the separately confirmed author profile rather than name matches.
    records.append({
        "id": "ck_author_duplicate",
        "concept_id": "duplicate_author_name",
        "canonical_concept_id": "duplicate_author_name",
        "statement": "The author and creator of FINZANJIR is Salamat Smaylov.",
        "aliases": ["FINZANJIR muallifi kim"],
        "evidence": {"status": "supported"},
        "provenance": [{"source": "unrelated_project_text"}],
        "reconciliation": {"status": "canonical"},
    })
    ai = FINZANJIRAI(build_knowledge_index(records))
    provider = UnavailableProvider()
    ai.language_model = provider
    ai.answer_generator.provider = provider
    return ai


def test_author_identity_question_uses_single_confirmed_fact():
    result = _engine_with_author_profile().answer(
        "FINZANJIR muallifi kim?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_deterministic_fallback"
    assert result.answer.citations == ("author_0001",)
    assert "Salamat Smaylov" in result.answer.answer
    assert "The author and creator" not in result.answer.answer


def test_author_biography_question_composes_distinct_profile_facts():
    result = _engine_with_author_profile().answer(
        "Salamat Smaylov haqida aytib ber",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_deterministic_fallback"
    assert set(result.answer.citations) == {
        "author_0001", "author_0002", "author_0003", "author_0004", "author_0006", "author_0007"
    }
    assert "astronomiya" in result.answer.answer
    assert "moliyaviy yo'qotishlar" in result.answer.answer
    assert "otasi Termuxni topish va o‘rnatish" in result.answer.answer
    assert "ATMOS va SINBAD" in result.answer.answer
    assert "The author and creator" not in result.answer.answer


def test_author_motivation_question_selects_only_motivation_evidence():
    result = _engine_with_author_profile().answer(
        "Muallif nima uchun FINZANJIRni yaratgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_motivation_grounded"
    assert result.answer.citations == ("author_0004",)
    assert "bank cheklovlari" in result.answer.answer
    assert "qonuniy tranzaksiyalarni" in result.answer.answer
    assert "false positive" in result.answer.answer
    assert "false negative" in result.answer.answer
    assert "fuqaro murojaatlarini" in result.answer.answer
    assert "Kiber Qalqon" in result.answer.answer
    assert "mustaqil tekshirmagan" in result.answer.answer
    assert "100 foiz xatosizlikni va'da qilish emas" in result.answer.answer
    assert "avtomatik bloklash buyrug'i ham emas" in result.answer.answer
    assert "2003-yil" not in result.answer.answer


class ExplodingProvider:
    last_status = "ready"

    @staticmethod
    def can_send_text(_text):
        return True

    @staticmethod
    def expand_question(_question):
        return ()

    @staticmethod
    def generate_json(**_kwargs):
        raise AssertionError("Author motivation must use its source-grounded answer, not free-form generation")


def test_author_motivation_answer_preserves_exact_family_story_and_unknown_cause():
    ai = _engine_with_author_profile()
    ai.language_model = ExplodingProvider()
    ai.answer_generator.provider = ExplodingProvider()

    result = ai.answer(
        "Muallif nima uchun FINZANJIRni yaratgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )

    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_motivation_grounded"
    assert result.answer.provider_status == "not_attempted"
    assert result.answer.citations == ("author_0004",)
    assert "oilaviy davrada eshitilgan voqea" in result.answer.answer
    assert "mustaqil tekshirmagan" in result.answer.answer
    assert "nima sababdan bloklanganini bilmaydi" in result.answer.answer
    assert "bank xatosi yoki noqonuniy harakat isboti emas" in result.answer.answer
    assert "qonuniy tranzaksiyalarni asossiz to'xtatmaslik" in result.answer.answer
    assert "false positive va false negative" in result.answer.answer
    assert "fuqaro murojaatlarini tez, adolatli qayta ko'rib chiqishga" in result.answer.answer
    assert "banklarni ayblash" in result.answer.answer
    assert "100 foiz xatosizlikni va'da qilish emas" in result.answer.answer


def test_project_origin_question_does_not_misstate_family_story_as_bank_fault():
    result = _engine_with_author_profile().answer(
        "FINZANJIR nima uchun yaratilgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )

    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_motivation_grounded"
    assert result.answer.citations == ("author_0004",)
    assert "karta aynan nima sababdan bloklanganini bilmaydi" in result.answer.answer
    assert "bank xatosi yoki noqonuniy harakat isboti emas" in result.answer.answer


def test_author_motivation_answer_is_localized_for_supported_languages():
    ai = _engine_with_author_profile()
    for question, phrase in (
        ("Почему автор создал FINZANJIR?", "не проверял эту историю"),
        ("Why did the author create FINZANJIR?", "did not independently investigate"),
        ("Автор FINZANJIR-ді не үшін жасады?", "өз бетінше тексермеген"),
        ("Avtor FINZANJIR di ne ushin jaratqan?", "teksermegen"),
    ):
        result = ai.answer(question, runtime_refs=(), working_memory_scope="author-test")
        assert result.answer.abstained is False
        assert result.answer.generation_mode == "author_motivation_grounded"
        assert phrase in result.answer.answer
