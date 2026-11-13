from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_project_principle_records
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def _grounded(query: str):
    index = build_knowledge_index(load_project_principle_records())
    retrieved = HybridRetriever(index).search(query, top_k=10)
    return GroundedContextAssembler(index).assemble(retrieved, query=query)


def test_project_question_retrieves_non_accusatory_signal_principle():
    context = _grounded("FINZANJIR fuqaroni firibgar deb topadimi")
    assert context.items
    assert any(item.record_id == "project_0002" for item in context.items)


def test_project_question_retrieves_bank_authority_boundary():
    context = _grounded("FINZANJIR bank kartasini o'zi bloklay oladimi")
    assert context.items
    assert any(item.record_id == "project_0004" for item in context.items)


def test_project_question_retrieves_citizen_appeal_and_resolution():
    context = _grounded("qonuniy tranzaksiya xato shubhali bo'lsa fuqaro murojaati")
    assert context.items
    assert any(item.record_id == "project_0006" for item in context.items)


def test_project_question_retrieves_minimal_data_principle():
    context = _grounded("FINZANJIR bank va fuqaro ma'lumotlarini minimallashtirish")
    assert context.items
    assert any(item.record_id == "project_0007" for item in context.items)
