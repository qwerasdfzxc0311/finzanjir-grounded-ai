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
        "author_0001", "author_0002", "author_0003", "author_0004"
    }
    assert "astronomiya" in result.answer.answer
    assert "moliyaviy yo'qotishlar" in result.answer.answer
    assert "The author and creator" not in result.answer.answer


def test_author_motivation_question_selects_only_motivation_evidence():
    result = _engine_with_author_profile().answer(
        "Muallif nima uchun FINZANJIRni yaratgan?",
        runtime_refs=(),
        working_memory_scope="author-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "author_deterministic_fallback"
    assert result.answer.citations == ("author_0004",)
    assert "bank cheklovlari" in result.answer.answer
    assert "qonuniy tranzaksiyasi" in result.answer.answer
    assert "false positive" in result.answer.answer
    assert "false negative" in result.answer.answer
    assert "fuqaro murojaati" in result.answer.answer
    assert "alohida" in result.answer.answer
    assert "bloklash buyrug'i deb qabul qilmaslik" in result.answer.answer
    assert "Kiber Qalqon" in result.answer.answer
    assert "mustaqil tekshirilmagan" in result.answer.answer
    assert "100 foiz xatosizlikni kafolatlashni emas" in result.answer.answer
    assert "yangi bloklash tizimi" in result.answer.answer
    assert "2003-yil" not in result.answer.answer
