from finzanjir_ai.offline.fallback import OfflineAnswerRouter
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


def test_offline_router_returns_retrieval_only_answer_when_primary_unavailable():
    context = GroundedContext(items=(
        GroundedContextItem(
            record_id="ck-1",
            concept_id="c1",
            statement="Fraud signal requires evidence.",
            score=0.8,
            provenance=({"source": "source-a"},),
            evidence={"status": "supported"},
        ),
    ))

    result = OfflineAnswerRouter().answer(
        "Why is evidence required?",
        context,
        primary_available=False,
    )

    assert result.mode == "retrieval_only"
    assert result.answer.abstained is False
    assert result.answer.citations == ("ck-1",)


def test_offline_router_abstains_without_context():
    result = OfflineAnswerRouter().answer(
        "Unknown question",
        GroundedContext(items=()),
        primary_available=False,
    )

    assert result.mode == "abstention"
    assert result.answer.abstained is True
