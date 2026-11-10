from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever
from finzanjir_ai.retrieval.rerank import Reranker
from finzanjir_ai.runtime.context import RuntimeContext
from finzanjir_ai.orchestration.ai import GroundedAI


def test_ai_orchestrator_runs_retrieval_grounding_and_answer_without_knowledge_write():
    records = [{"id":"ck-1","concept_id":"c1","canonical_concept_id":"c1","statement":"Evidence supports risk assessment.","aliases":["risk evidence"],"evidence":{"status":"supported"},"provenance":["source-a"],"reconciliation":{}}]
    index = build_knowledge_index(records)
    ai = GroundedAI(HybridRetriever(index), Reranker(index), GroundedContextAssembler(index), GroundedAnswerGenerator())
    result = ai.answer("risk evidence", RuntimeContext.from_refs(knowledge_refs=("ck-1",), runtime_refs=("sig-1",), working_memory_scope="case-1"))
    assert result.abstained is False
    assert result.citations == ("ck-1",)
    assert result.runtime_refs == ("sig-1",)
