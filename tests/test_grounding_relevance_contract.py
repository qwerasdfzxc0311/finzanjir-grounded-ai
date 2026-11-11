from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import RetrievalResult


def test_orchestrator_abstains_when_retrieval_is_only_weakly_relevant():
    index = build_system_flow().demo_knowledge_index()

    result = FINZANJIRAI(index).answer(
        "Unsupported fact with no grounded evidence",
        runtime_refs=(),
        working_memory_scope="test",
    )

    assert result.answer.abstained is True
    assert result.answer.confidence < 0.35
    assert result.answer.citations == ()


def test_orchestrator_keeps_strongly_relevant_grounding():
    index = build_system_flow().demo_knowledge_index()

    result = FINZANJIRAI(index).answer(
        "Why does case escalation require evidence?",
        runtime_refs=(),
        working_memory_scope="test",
    )

    assert result.answer.abstained is False
    assert result.answer.confidence >= 0.35
    assert result.answer.citations



def test_grounding_accepts_canonical_source_derived_evidence():
    index = build_knowledge_index([
        {
            "id": "ck-source-derived",
            "concept_id": "c1",
            "canonical_concept_id": "c1",
            "statement": "FINZANJIR uses evidence before escalation.",
            "aliases": ["evidence escalation"],
            "evidence": {"status": "source_derived", "sources": [{"source_id": "doc-1"}]},
            "provenance": [{"source": "doc-1"}],
            "reconciliation": {},
        },
        {
            "id": "ck-observed",
            "concept_id": "c2",
            "canonical_concept_id": "c2",
            "statement": "Observed but not authoritative.",
            "aliases": ["observed"],
            "evidence": {"status": "observed"},
            "provenance": [{"source": "test"}],
            "reconciliation": {},
        },
    ])

    results = (
        RetrievalResult("ck-source-derived", 0.9, 1.0, 0.8),
        RetrievalResult("ck-observed", 0.95, 1.0, 0.9),
    )
    grounded = GroundedContextAssembler(index).assemble(results)

    assert tuple(item.record_id for item in grounded.items) == ("ck-source-derived",)


def test_grounding_rejects_source_derived_record_with_unconfirmed_status_marker():
    index = build_knowledge_index([
        {
            "id": "ck-unconfirmed",
            "concept_id": "c1",
            "canonical_concept_id": "c1",
            "statement": "Ushbu qatlamning amaldagi mavjudligi tasdiqlanmagan.",
            "aliases": ["case evidence"],
            "evidence": {
                "status": "source_derived",
                "verification": "unconfirmed",
                "sources": [{"source_id": "doc-1"}],
            },
            "provenance": [{"source": "doc-1"}],
            "reconciliation": {},
        },
        {
            "id": "ck-confirmed",
            "concept_id": "c2",
            "canonical_concept_id": "c2",
            "statement": "Case escalation supporting evidence bilan asoslanadi.",
            "aliases": ["case evidence escalation"],
            "evidence": {
                "status": "source_derived",
                "verification": "confirmed",
                "sources": [{"source_id": "doc-2"}],
            },
            "provenance": [{"source": "doc-2"}],
            "reconciliation": {},
        },
    ])

    results = (
        RetrievalResult("ck-unconfirmed", 0.95, 1.0, 0.8),
        RetrievalResult("ck-confirmed", 0.8, 1.0, 0.7),
    )
    grounded = GroundedContextAssembler(index).assemble(results)

    assert tuple(item.record_id for item in grounded.items) == ("ck-confirmed",)
