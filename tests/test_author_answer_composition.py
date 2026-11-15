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
        "author_0001", "author_0002", "author_0003", "author_0004", "author_0006", "author_0007", "author_0008", "author_0009"
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
    assert result.answer.citations == ("author_0004", "author_0008", "author_0009")
    assert "hayotiy tajribalari" in result.answer.answer
    assert "moliyaviy xavfsizlikka oid tashvishlari" in result.answer.answer
    assert "jamiyatga foyda keltirish istagini" in result.answer.answer
    assert "insoniylik va adolat" in result.answer.answer
    assert "moliyaviy va kiberxavfsizlik bo'yicha bilim" in result.answer.answer
    assert "Kiber Qalqon" in result.answer.answer
    assert "100 foiz hal qilishga va’da bermaydi" in result.answer.answer
    assert "Firibgarlikni qiyinlashtirish, qonuniy hayotni esa qiyinlashtirmaslik" in result.answer.answer
    assert "oilaviy davrada eshitilgan" not in result.answer.answer
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


def test_author_motivation_answer_uses_full_summary_without_overweighting_anecdote():
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
    assert result.answer.citations == ("author_0004", "author_0008", "author_0009")
    assert "hayotiy tajribalari" in result.answer.answer
    assert "jamiyatga foyda keltirish istagini" in result.answer.answer
    assert "Kiber Qalqon" in result.answer.answer
    assert "insoniylik va adolat" in result.answer.answer
    assert "100 foiz hal qilishga va'da bermaydi" in result.answer.answer
    assert "oilaviy davrada eshitilgan" not in result.answer.answer

def test_project_origin_question_uses_broad_motivation_summary():
    result = _engine_with_author_profile().answer(
        "FINZANJIR nima uchun yaratilgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )

    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_motivation_grounded"
    assert result.answer.citations == ("author_0004", "author_0008", "author_0009")
    assert "hayotiy tajribalari" in result.answer.answer
    assert "Firibgarlikni qiyinlashtirish, qonuniy hayotni esa qiyinlashtirmaslik" in result.answer.answer
    assert "oilaviy davrada eshitilgan" not in result.answer.answer

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



def test_semantically_similar_author_purpose_questions_use_the_same_grounded_answer():
    ai = _engine_with_author_profile()
    questions = (
        "FINZANJIRning asosiy maqsadi nima?",
        "FINZANJIR loyihasini yaratishdan ko'zlangan maqsad nima?",
        "Muallif nima sababdan FINZANJIRni yaratishga qaror qilgan?",
        "Why was FINZANJIR created?",
        "Почему был создан FINZANJIR?",
        "Автор FINZANJIR-ді не үшін жасады?",
        "Muallif FINZANJIRdi ne ushın jaratqan?",
    )
    for question in questions:
        result = ai.answer(
            question,
            runtime_refs=(),
            working_memory_scope="author-purpose-variants",
        )
        assert result.answer.abstained is False, question
        assert result.answer.generation_mode == "author_motivation_grounded", question
        assert result.answer.citations == ("author_0004", "author_0008", "author_0009"), question
        assert "FINZANJIR" in result.answer.answer or "FINZANJIR" in question


def test_author_name_or_critique_question_does_not_trigger_motivation_answer():
    from finzanjir_ai.orchestration.intent import is_author_motivation_query

    assert not is_author_motivation_query("Salamat Smaylov kim?")
    assert not is_author_motivation_query("Muallif nima uchun bunday deydi?")
    assert not is_author_motivation_query("FINZANJIR nima uchun kerak?")
    assert not is_author_motivation_query("Muallif FINZANJIRni haddan tashqari maqtaydimi?")
    assert not is_author_motivation_query("Salamat Smaylov loyihani tanqid qiladimi?")


def test_author_motivation_accepts_common_ushun_spelling_and_returns_full_answer():
    result = _engine_with_author_profile().answer(
        "Siz Muallif nima ushun yaratgan finzanjirni",
        runtime_refs=(),
        working_memory_scope="author-purpose-ushun",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_motivation_grounded"
    assert result.answer.citations == ("author_0004", "author_0008", "author_0009")
    assert "hayotiy tajribalari" in result.answer.answer
    assert "jamiyatga foyda keltirish istagi" in result.answer.answer
    assert "Firibgarlikni qiyinlashtirish, qonuniy hayotni esa qiyinlashtirmaslik" in result.answer.answer
    assert "oilaviy davrada eshitilgan" not in result.answer.answer
