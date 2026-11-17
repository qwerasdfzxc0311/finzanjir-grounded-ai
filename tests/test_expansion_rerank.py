from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.hybrid import HybridRetriever
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker


def test_alias_expansion_adds_known_aliases_and_reranking_boosts_alias_match():
    index = build_knowledge_index([
        {"id": "ck-1", "concept_id": "c1", "canonical_concept_id": "c1", "statement": "Fraud signal requires evidence.", "aliases": ["suspicious signal"], "evidence": {}, "provenance": [], "reconciliation": {}},
        {"id": "ck-2", "concept_id": "c2", "canonical_concept_id": "c2", "statement": "Risk review uses evidence.", "aliases": ["risk assessment"], "evidence": {}, "provenance": [], "reconciliation": {}},
    ])
    expanded = QueryExpander(index).expand("suspicious")
    assert "suspicious signal" in expanded

    results = HybridRetriever(index).search("suspicious", top_k=2)
    reranked = Reranker(index).rerank("suspicious", results)
    assert reranked[0].record_id == "ck-1"



def test_project_mission_architecture_comparison_and_limits_get_targeted_hints():
    expander = QueryExpander(build_knowledge_index([]))
    mission = expander.expand(
        "FINZANJIRning hujjatlarda tasdiqlangan maqsadi, arxitekturasi va ishlash mexanizmlari qanday?"
    )
    comparison = expander.expand(
        "FINZANJIRning O‘zbekistondagi va boshqa davlatlardagi o‘xshash loyihalardan farqi nimada?"
    )
    limitations = expander.expand(
        "FINZANJIRning kuchli jihatlari va cheklovlari nimalardan iborat?"
    )
    assert any("hujjatlarda tasdiqlangan maqsad" in item for item in mission)
    assert any("arxitektura qatlamlari" in item for item in mission)
    assert any("xalqaro o'xshash loyihalar" in item for item in comparison)
    assert any("cross-bank fraud detection" in item for item in comparison)
    assert any("kuchli tomonlari" in item for item in limitations)
    assert any("production readiness" in item for item in limitations)
