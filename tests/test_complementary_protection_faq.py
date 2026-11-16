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
