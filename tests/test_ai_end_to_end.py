import pytest

from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.pipeline import process_transaction
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


def test_end_to_end_synthetic_transaction_to_grounded_ai_explanation():
    transaction = {
        "transaction_id": "syn-tx-e2e",
        "bank_id": "bank-demo",
        "actor_id": "actor-e2e",
        "amount": 2500,
        "currency": "UZS",
        "occurred_at": "2026-11-11T00:00:01Z",
        "channel": "mobile",
        "status": "AUTHORIZED",
        "synthetic": True,
    }

    pipeline = process_transaction(
        transaction,
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert pipeline.signal is not None
    assert pipeline.evidence is not None
    assert pipeline.risk is not None
    assert pipeline.case is not None

    manager = CaseManager()
    case = manager.open_case(
        case_id=pipeline.case["id"],
        signal_ids=pipeline.case["signal_ids"],
        risk_id=pipeline.case["risk_id"],
        threshold_id=pipeline.case["threshold_id"],
        transaction_id=transaction["transaction_id"],
        escalation_met=True,
    )
    assert case["status"] == "OPEN"

    index = build_knowledge_index(
        [{
            "id": "ck-e2e",
            "concept_id": "c-e2e",
            "canonical_concept_id": "c-e2e",
            "statement": "A case requires supporting evidence and an escalation threshold.",
            "aliases": ["case escalation"],
            "evidence": {"status": "supported"},
            "provenance": [{"source": "canonical-v0.6"}],
            "reconciliation": {},
        }]
    )
    result = FINZANJIRAI(index).answer(
        "Why does a case require evidence and escalation?",
        runtime_refs=(transaction["transaction_id"], pipeline.signal["id"], pipeline.case["id"]),
        working_memory_scope=pipeline.case["id"],
    )

    assert result.answer.abstained is False
    assert result.answer.citations == ("ck-e2e",)
    assert result.runtime_context.can_write_authoritative_knowledge is False


def test_adversarial_cases_are_safe():
    with pytest.raises(ValueError, match="synthetic"):
        process_transaction(
            {
                "transaction_id": "real-looking",
                "bank_id": "bank-demo",
                "actor_id": "actor-1",
                "amount": 2500,
                "currency": "UZS",
                "occurred_at": "2026-11-11T00:00:01Z",
                "channel": "mobile",
                "status": "AUTHORIZED",
                "synthetic": False,
            },
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )

    empty = GroundedAnswerGenerator().generate(
        "Unknown",
        __import__("finzanjir_ai.retrieval.grounding", fromlist=["GroundedContext"]).GroundedContext(items=()),
    )
    assert empty.abstained is True
    assert empty.confidence == 0


def test_grounded_ai_abstains_when_available_evidence_is_too_weak():
    context = GroundedContext(items=(
        GroundedContextItem(
            record_id="ck-weak",
            concept_id="c-weak",
            statement="Weakly related statement.",
            score=0.05,
            provenance=({"source": "test"},),
            evidence={"status": "observed"},
        ),
    ))

    result = GroundedAnswerGenerator().generate("Unrelated question", context)

    assert result.abstained is True
    assert result.confidence < 0.35
