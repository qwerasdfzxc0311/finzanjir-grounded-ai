from __future__ import annotations

from typing import Any

from finzanjir_ai.audit.service import AuditLog, calculate_kpis
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.cross_bank.matcher import CrossBankMatcher
from finzanjir_ai.knowledge.index import KnowledgeIndex
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.pipeline import process_transaction


def run_full_demo(transaction: dict[str, Any], *, knowledge_index: KnowledgeIndex) -> dict[str, Any]:
    pipeline = process_transaction(transaction, signal_amount_threshold=1000, escalation_threshold=0.75)
    manager = CaseManager()
    case = None
    decision = None
    audit = AuditLog()

    if pipeline.case is not None:
        case = manager.open_case(
            case_id=pipeline.case["id"],
            signal_ids=pipeline.case["signal_ids"],
            risk_id=pipeline.case["risk_id"],
            threshold_id=pipeline.case["threshold_id"],
            transaction_id=transaction["transaction_id"],
            escalation_met=True,
        )
        decision = manager.apply_human_decision(
            case_id=case["case_id"],
            actor_id="demo-reviewer",
            decision="APPROVE_ACTION",
            reason="Synthetic demo evidence supports continued review.",
        )
        audit.append(
            actor_id="demo-reviewer",
            event_type="HumanDecisionApplied",
            object_type="HumanDecision",
            object_id=decision["human_decision"]["decision_id"],
            details={"decision": decision["human_decision"]["decision"]},
        )

    cross_bank = CrossBankMatcher().match(
        [
            {"id": f"{transaction['transaction_id']}-sig-a", "bank_id": transaction["bank_id"], "correlation_key": "demo-device-1"},
            {"id": f"{transaction['transaction_id']}-sig-b", "bank_id": "bank-b", "correlation_key": "demo-device-1"},
        ],
        authorized=True,
    )

    ai = FINZANJIRAI(knowledge_index).answer(
        "Why was this transaction escalated?",
        runtime_refs=(transaction["transaction_id"],),
        working_memory_scope=case["case_id"] if case else transaction["transaction_id"],
    )
    kpi = calculate_kpis(
        signals_detected=1 if pipeline.signal else 0,
        cases_opened=1 if case else 0,
        cases_actioned=1 if decision else 0,
        review_seconds_total=120 if decision else 0,
        data_mode="synthetic",
    )
    return {
        "pipeline": pipeline,
        "case": case,
        "decision": decision,
        "audit": audit.events(),
        "cross_bank": cross_bank,
        "ai": ai,
        "kpi": kpi,
    }
