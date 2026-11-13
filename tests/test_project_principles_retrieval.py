from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_project_principle_records
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def _retrieved(query: str):
    index = build_knowledge_index(load_project_principle_records())
    results = HybridRetriever(index).search(query, top_k=10)
    return index, query, results


def _assert_grounded(index, query, results, record_id):
    assert any(item.record_id == record_id for item in results)
    context = GroundedContextAssembler(index).assemble(results, query=query)
    assert any(item.record_id == record_id for item in context.items)


def test_project_question_retrieves_non_accusatory_signal_principle():
    query = "fuqaroni firibgar deb topadimi"
    index, query, results = _retrieved(query)
    _assert_grounded(index, query, results, "project_0002")


def test_project_question_retrieves_bank_authority_boundary():
    query = "bank kartasini o'zi bloklay oladimi"
    index, query, results = _retrieved(query)
    _assert_grounded(index, query, results, "project_0004")


def test_project_question_retrieves_citizen_appeal_and_resolution():
    query = "qonuniy tranzaksiya xato shubhali bo'lsa fuqaro murojaati"
    index, query, results = _retrieved(query)
    _assert_grounded(index, query, results, "project_0006")


def test_project_question_retrieves_minimal_data_principle():
    query = "bank va fuqaro ma'lumotlarini minimallashtirish"
    index, query, results = _retrieved(query)
    _assert_grounded(index, query, results, "project_0007")
