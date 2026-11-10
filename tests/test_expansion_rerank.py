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
