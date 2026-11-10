from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def test_hybrid_retrieval_combines_term_and_concept_evidence():
    records = [
        {"id": "ck-1", "concept_id": "c1", "canonical_concept_id": "c1", "statement": "Fraud signal requires evidence.", "aliases": ["suspicious signal"], "evidence": {}, "provenance": [], "reconciliation": {}},
        {"id": "ck-2", "concept_id": "c2", "canonical_concept_id": "c2", "statement": "Risk assessment uses evidence.", "aliases": ["risk evidence"], "evidence": {}, "provenance": [], "reconciliation": {}},
    ]
    retriever = HybridRetriever(build_knowledge_index(records))
    results = retriever.search("suspicious signal evidence", top_k=2)
    assert results[0].record_id == "ck-1"
    assert results[0].score >= results[1].score
