from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem
from finzanjir_ai.answer.service import GroundedAnswerService


def test_grounded_answer_returns_confidence_and_citations():
    context = GroundedContext(items=(GroundedContextItem("ck-1", "c1", "Fraud signal requires evidence.", 1.0, ({"source": "a"},), {"status": "supported"}),))
    result = GroundedAnswerService().answer("What is required?", context)
    assert result.abstained is False
    assert result.confidence == 1.0
    assert result.citations == ("ck-1",)
    assert "Fraud signal requires evidence." in result.answer


def test_grounded_answer_abstains_without_grounded_context():
    result = GroundedAnswerService().answer("Unknown", GroundedContext(items=()))
    assert result.abstained is True
    assert result.citations == ()
