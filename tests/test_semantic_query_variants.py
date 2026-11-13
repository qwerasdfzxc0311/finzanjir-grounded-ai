from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever


def test_expanded_query_can_retrieve_synonymous_project_concept():
    index = build_knowledge_index([{
        "id": "ck-protection",
        "concept_id": "concept-protection",
        "canonical_concept_id": "concept-protection",
        "statement": "FINZANJIR fuqarolarning moliyaviy mablag'larini firibgarlikdan himoya qilishga yordam beradi.",
        "aliases": ["moliyaviy xavfsizlik", "firibgarlikdan himoya"],
        "evidence": {"status": "supported"},
        "provenance": [{"source": "canonical-v0.6"}],
        "reconciliation": {},
    }])
    retriever = HybridRetriever(index)
    results = retriever.search("fuqarolarning moliyaviy mablag'larini himoya qilish", top_k=5)
    context = GroundedContextAssembler(index).assemble(
        results,
        query="Pulimni qanday asraysiz?",
        query_alternatives=("fuqarolarning moliyaviy mablag'larini himoya qilish",),
    )
    assert len(context.items) == 1
    assert context.items[0].record_id == "ck-protection"
    assert "moliyaviy xavfsizlik" in context.items[0].aliases
