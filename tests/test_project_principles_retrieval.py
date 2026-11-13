from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.knowledge.loader import load_project_principle_records
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def _retrieved(query: str):
    index = build_knowledge_index(load_project_principle_records())
    results = HybridRetriever(index).search(query, top_k=10)
    return index, results


def test_project_question_retrieves_non_accusatory_signal_principle():
    index, results = _retrieved("fuqaroni firibgar deb topadimi")
    assert any(item.record_id == "project_0002" for item in results)
    context = GroundedContextAssembler(index).assemble(results)
    assert any(item.record_id == "project_0002" for item in context.items)


def test_project_question_retrieves_bank_authority_boundary():
    index, results = _retrieved("bank kartasini o'zi bloklay oladimi")
    assert any(item.record_id == "project_0004" for item in results)
    context = GroundedContextAssembler(index).assemble(results)
    assert any(item.record_id == "project_0004" for item in context.items)


def test_project_question_retrieves_citizen_appeal_and_resolution():
    index, results = _retrieved("qonuniy tranzaksiya xato shubhali bo'lsa fuqaro murojaati")
    assert any(item.record_id == "project_0006" for item in results)
    context = GroundedContextAssembler(index).assemble(results)
    assert any(item.record_id == "project_0006" for item in context.items)


def test_project_question_retrieves_minimal_data_principle():
    index, results = _retrieved("bank va fuqaro ma'lumotlarini minimallashtirish")
    assert any(item.record_id == "project_0007" for item in results)
    context = GroundedContextAssembler(index).assemble(results)
    assert any(item.record_id == "project_0007" for item in context.items)
