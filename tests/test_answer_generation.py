from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


def test_grounded_answer_uses_evidence_and_citations():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-1",
        concept_id="c1",
        statement="Evidence supports risk assessment.",
        score=0.9,
        provenance=("source-a",),
        evidence={"status": "supported"},
    ),))
    result = GroundedAnswerGenerator().generate("Why?", context)
    assert result.abstained is False
    assert result.confidence > 0
    assert result.citations == ("ck-1",)


def test_answer_abstains_without_grounding_context():
    result = GroundedAnswerGenerator().generate("Unknown?", GroundedContext(items=()))
    assert result.abstained is True
    assert result.confidence == 0.0
