from dataclasses import replace

from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.hybrid import RetrievalResult
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler


def test_grounding_preserves_provenance_and_filters_rejected_evidence():
    index = build_knowledge_index([
        {"id": "ck-1", "concept_id": "c1", "canonical_concept_id": "c1", "statement": "Supported fraud evidence.", "aliases": [], "evidence": {"status": "supported"}, "provenance": [{"source": "source-a"}], "reconciliation": {}},
        {"id": "ck-2", "concept_id": "c2", "canonical_concept_id": "c2", "statement": "Rejected claim.", "aliases": [], "evidence": {"status": "rejected"}, "provenance": [{"source": "source-b"}], "reconciliation": {}},
    ])
    results = (RetrievalResult("ck-1", 1.0, 1.0, 1.0), RetrievalResult("ck-2", 0.9, 0.9, 0.9))

    context = GroundedContextAssembler(index).assemble(results)

    assert [item.record_id for item in context.items] == ["ck-1"]
    assert context.items[0].provenance == ({"source": "source-a"},)
