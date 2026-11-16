from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_project_principle_records
from finzanjir_ai.orchestration.intent import classify_query_intent, is_project_overview_query
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def _retrieve(query: str):
    index = build_knowledge_index(load_project_principle_records())
    results = HybridRetriever(index).search(query, top_k=10)
    return index, results


def test_complementary_protection_question_retrieves_author_confirmed_record():
    query = "FINZANJIR nima uchun kerak?"
    index, results = _retrieve(query)
    assert any(item.record_id == "project_0010" for item in results)
    context = GroundedContextAssembler(index).assemble(results, query=query)
    assert any(item.record_id == "project_0010" for item in context.items)
    record = index.get_record("project_0010")
    assert record is not None
    assert "antiviruslarning o'rnini egallash uchun emas" in record.statement
    assert "hovlidagi ekinni" in record.statement


def test_sponsorship_question_retrieves_complementary_defense_rationale():
    query = "Nima uchun FINZANJIRga homiylik qilish kerak?"
    index, results = _retrieve(query)
    assert any(item.record_id == "project_0011" for item in results)
    record = index.get_record("project_0011")
    assert record is not None
    assert "bitta himoya qatlamining mavjudligi" in record.statement
    assert "homiylik bank ma'lumotlariga avtomatik kirish" in record.statement


def test_foreign_copy_question_retrieves_comparison_boundary():
    query = "FINZANJIR boshqa davlatlarda bormi? U nusxami?"
    index, results = _retrieve(query)
    assert any(item.record_id == "project_0012" for item in results)
    record = index.get_record("project_0012")
    assert record is not None
    assert "nusxa olinganini anglatmaydi" in record.statement
    assert "ishonchli manbalar asosida alohida taqqoslash" in record.statement


def test_legality_question_retrieves_legal_boundary_not_an_approval_claim():
    query = "FINZANJIR qonuniymi?"
    index, results = _retrieve(query)
    assert any(item.record_id == "project_0013" for item in results)
    record = index.get_record("project_0013")
    assert record is not None
    assert "avtomatik ravishda qonuniy degani emas" in record.statement
    assert "qonuniy deb tasdiqlangan deb aytilmasligi kerak" in record.statement


def test_specific_finzanjir_faq_questions_do_not_use_generic_overview_route():
    questions = (
        "FINZANJIR nima uchun kerak?",
        "Nima uchun FINZANJIRga homiylik qilish kerak?",
        "FINZANJIR boshqa davlatlarda bormi? U nusxami?",
        "FINZANJIR qonuniymi?",
    )
    for query in questions:
        assert classify_query_intent(query) == "project", query
        assert not is_project_overview_query(query), query


def test_plain_finzanjir_overview_still_uses_the_dedicated_overview_route():
    assert classify_query_intent("FINZANJIR nima?") == "project_overview"
    assert is_project_overview_query("FINZANJIR nima?")


class UnavailableProvider:
    last_status = "provider_failed"

    @staticmethod
    def can_send_text(_text):
        return True

    @staticmethod
    def generate_json(**_kwargs):
        return None


def test_canonical_faq_answers_are_returned_only_with_matching_grounded_evidence():
    from finzanjir_ai.answer.generator import GroundedAnswerGenerator

    cases = (
        (
            "FINZANJIR nima uchun kerak?",
            "project_0010",
            "antiviruslarning o'rnini egallash uchun emas",
            "hovlidagi ekin",
        ),
        (
            "Nima uchun FINZANJIRga homiylik qilish kerak?",
            "project_0011",
            "bitta himoya qatlamining mavjudligi",
            "Homiylik bank ma'lumotlariga avtomatik kirish",
        ),
        (
            "FINZANJIR boshqa davlatlarda bormi? U nusxami?",
            "project_0012",
            "aynan ulardan nusxa olingan degani emas",
            "ishonchli manbalar asosida alohida taqqoslash",
        ),
        (
            "FINZANJIR qonuniymi?",
            "project_0013",
            "avtomatik ravishda qonuniy degani emas",
            "huquqiy tekshiruv",
        ),
    )
    for query, record_id, expected_one, expected_two in cases:
        index, results = _retrieve(query)
        context = GroundedContextAssembler(index).assemble(results, query=query)
        result = GroundedAnswerGenerator(UnavailableProvider()).generate(query, context)
        assert result.abstained is False, query
        assert result.generation_mode == "complementary_protection_faq_localized", query
        assert result.citations == (record_id,), query
        assert expected_one in result.answer, query
        assert expected_two in result.answer, query


def test_canonical_faq_does_not_trigger_without_its_matching_source_record():
    from finzanjir_ai.answer.generator import GroundedAnswerGenerator
    from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem

    context = GroundedContext(items=(GroundedContextItem(
        record_id="project_0007",
        concept_id="finzanjir_data_minimization_security",
        statement="FINZANJIR minimal ma'lumot bilan ishlashi kerak.",
        score=0.9,
        provenance=({"source": "author-confirmed"},),
        evidence={"status": "project_source", "verification": "author_confirmed"},
    ),))
    result = GroundedAnswerGenerator(UnavailableProvider()).generate(
        "FINZANJIR qonuniymi?", context
    )
    assert result.generation_mode != "complementary_protection_faq_localized"
