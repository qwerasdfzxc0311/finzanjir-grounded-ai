from finzanjir_ai.audit.service import AuditLog, calculate_kpis
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.cross_bank.matcher import CrossBankMatcher
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.pipeline import process_transaction
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


def test_full_demo_chain_connects_transaction_to_case_audit_cross_bank_and_ai():
    tx = {"transaction_id": "syn-full-1", "bank_id": "bank-a", "actor_id": "actor-1", "amount": 2500, "currency": "UZS", "occurred_at": "2026-11-11T00:00:01Z", "channel": "mobile", "status": "AUTHORIZED", "synthetic": True, "signal_events": build_synthetic_case_signal_events(transaction_id="syn-full-1", observed_at="2026-11-11T00:00:01Z"), "shadow_mode": False}
    pipeline = process_transaction(tx, signal_amount_threshold=1000, escalation_threshold=0.75)
    assert pipeline.case is not None

    manager = CaseManager()
    manager.open_case(case_id=pipeline.case["id"], signal_ids=pipeline.case["signal_ids"], risk_id=pipeline.case["risk_id"], threshold_id=pipeline.case["threshold_id"], transaction_id=tx["transaction_id"], escalation_met=True)
    decision = manager.apply_human_decision(case_id=pipeline.case["id"], actor_id="reviewer-1", decision="APPROVE_ACTION", reason="Evidence supports continued review.")

    audit = AuditLog()
    audit.append(actor_id="reviewer-1", event_type="HumanDecisionApplied", object_type="HumanDecision", object_id=decision["human_decision"]["decision_id"], details={"decision": "APPROVE_ACTION"})

    cross = CrossBankMatcher().match([
        {"transaction_id": "tx-a", "bank_id": "bank-a", "device_id": "device-1"},
        {"transaction_id": "tx-b", "bank_id": "bank-b", "device_id": "device-1"},
    ], scope="cross_bank", authorized_exchange=True)
    assert len(cross.matches) == 1
    assert cross.matches[0]["scope"] == "cross_bank"

    index = build_knowledge_index([{"id": "ck-full", "concept_id": "c-full", "canonical_concept_id": "c-full", "statement": "A case requires supporting evidence and an escalation threshold.", "aliases": ["case escalation"], "evidence": {"status": "supported"}, "provenance": [{"source": "canonical-v0.6"}], "reconciliation": {}}])
    ai = FINZANJIRAI(index).answer("What does case escalation require?", runtime_refs=(tx["transaction_id"], pipeline.case["id"]), working_memory_scope=pipeline.case["id"])
    assert ai.answer.abstained is False
    assert ai.answer.citations == ("ck-full",)

    kpi = calculate_kpis(signals_detected=5, cases_opened=1, cases_actioned=1, review_seconds_total=120, data_mode="synthetic")
    assert kpi["signal_to_case_rate"] == 0.2
    assert len(audit.events()) == 1
