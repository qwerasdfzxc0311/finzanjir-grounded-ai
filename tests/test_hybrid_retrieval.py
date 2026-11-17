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


def test_bm25_lexical_score_is_not_reported_as_semantic_similarity():
    records = [
        {"id": "lex-1", "concept_id": "lex-1", "canonical_concept_id": "lex-1",
         "statement": "Rayleigh scattering explains blue sky.", "aliases": [],
         "evidence": {}, "provenance": [], "reconciliation": {}},
        {"id": "lex-2", "concept_id": "lex-2", "canonical_concept_id": "lex-2",
         "statement": "Financial fraud risk requires evidence.", "aliases": [],
         "evidence": {}, "provenance": [], "reconciliation": {}},
    ]
    results = HybridRetriever(build_knowledge_index(records)).search("blue sky", top_k=2)
    assert results
    assert all(item.semantic_score == 0.0 for item in results)
    assert any(item.lexical_score > 0 for item in results)


def test_hybrid_retrieval_matches_uzbek_inflections_by_conservative_stem():
    records = [
        {"id": "morph-1", "concept_id": "morph-1", "canonical_concept_id": "morph-1",
         "statement": "Fuqarolarning qonuniy mablag'larini himoya qilish muhim.",
         "aliases": [], "evidence": {}, "provenance": [], "reconciliation": {}},
        {"id": "morph-2", "concept_id": "morph-2", "canonical_concept_id": "morph-2",
         "statement": "Astronomiya sayyoralarni o'rganadi.",
         "aliases": [], "evidence": {}, "provenance": [], "reconciliation": {}},
    ]
    results = HybridRetriever(build_knowledge_index(records)).search(
        "Fuqarolar qonuniy mablag'ni himoyalash", top_k=2
    )
    assert results
    assert results[0].record_id == "morph-1"


def test_hybrid_retrieval_recovers_a_clear_single_character_typo_with_ngrams():
    records = [
        {"id": "typo-1", "concept_id": "typo-1", "canonical_concept_id": "typo-1",
         "statement": "Firibgarlik xavfini aniqlash uchun dalillar tekshiriladi.",
         "aliases": [], "evidence": {}, "provenance": [], "reconciliation": {}},
        {"id": "typo-2", "concept_id": "typo-2", "canonical_concept_id": "typo-2",
         "statement": "Astronomiya sayyoralarni o'rganadi.",
         "aliases": [], "evidence": {}, "provenance": [], "reconciliation": {}},
    ]
    results = HybridRetriever(build_knowledge_index(records)).search(
        "firibgarlk xavfini aniqlash", top_k=2
    )
    assert results
    assert results[0].record_id == "typo-1"
    assert all(item.semantic_score == 0.0 for item in results)
