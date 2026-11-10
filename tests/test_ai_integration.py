from finzanjir_ai.ai.orchestrator import GroundedAI
from finzanjir_ai.knowledge.index import build_knowledge_index


def test_grounded_ai_integrates_retrieval_grounding_and_runtime_context():
    index = build_knowledge_index([
        {"id": "ck-1", "concept_id": "c1", "canonical_concept_id": "c1", "statement": "Fraud signal requires evidence.", "aliases": ["suspicious signal"], "evidence": {"status": "supported"}, "provenance": [{"source": "source-a"}], "reconciliation": {}},
    ])
    ai = GroundedAI(index)
    result = ai.ask("suspicious signal", runtime_refs=("sig-1",), working_memory_scope="case-1")

    assert result.abstained is False
    assert result.knowledge_refs == ("ck-1",)
    assert result.runtime_refs == ("sig-1",)
    assert result.citations == ("ck-1",)
