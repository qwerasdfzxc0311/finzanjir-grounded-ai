from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


def test_grounded_answer_uses_context_and_emits_citations():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-1", concept_id="c1",
        statement="Fraud signal requires supporting evidence.",
        score=0.9, provenance=({"source": "source-a"},),
        evidence={"status": "supported"},
    ),))
    result = GroundedAnswerGenerator().generate("Why is evidence required?", context)
    assert result.abstained is False
    assert result.confidence > 0
    assert "Fraud signal requires supporting evidence." in result.answer
    assert result.citations == ("ck-1",)


def test_grounded_answer_abstains_without_grounded_context():
    result = GroundedAnswerGenerator().generate(
        "What is the answer?", GroundedContext(items=())
    )
    assert result.abstained is True
    assert result.confidence == 0
    assert result.citations == ()
    assert "yetarli" in result.answer.casefold()
