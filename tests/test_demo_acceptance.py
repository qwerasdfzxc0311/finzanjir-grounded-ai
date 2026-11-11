from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.prototype.demo import run_full_demo


def _knowledge():
    return build_knowledge_index([{
        "id": "ck-demo",
        "concept_id": "c-demo",
        "canonical_concept_id": "c-demo",
        "statement": "A case requires supporting evidence and an escalation threshold.",
        "aliases": ["case escalation"],
        "evidence": {"status": "supported"},
        "provenance": [{"source": "canonical-v0.6"}],
        "reconciliation": {},
    }])


def test_demo_suspicious_path_opens_case_and_keeps_synthetic_decision_non_authoritative():
    result = run_full_demo(
        {
            "transaction_id": "syn-demo-suspicious",
            "bank_id": "bank-a",
            "actor_id": "actor-a",
            "amount": 2500,
            "currency": "UZS",
            "occurred_at": "2026-11-11T00:00:01Z",
            "channel": "mobile",
            "status": "AUTHORIZED",
            "synthetic": True,
        },
        knowledge_index=_knowledge(),
    )
    assert result["case"] is not None
    assert result["decision"]["case"]["status"] == "OPEN"
    assert result["decision"]["human_decision"]["is_authoritative"] is False
    assert result["decision"]["human_decision"]["decision_origin"] == "synthetic_demo"
    assert result["ai"].answer.abstained is False
    assert result["kpi"]["data_mode"] == "synthetic"


def test_demo_normal_path_does_not_open_case():
    result = run_full_demo(
        {
            "transaction_id": "syn-demo-normal",
            "bank_id": "bank-a",
            "actor_id": "actor-a",
            "amount": 100,
            "currency": "UZS",
            "occurred_at": "2026-11-11T00:00:01Z",
            "channel": "mobile",
            "status": "AUTHORIZED",
            "synthetic": True,
        },
        knowledge_index=_knowledge(),
    )
    assert result["case"] is None
    assert result["decision"] is None
    assert result["kpi"]["signal_to_case_rate"] == 0.0
