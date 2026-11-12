from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finzanjir_ai.audit.service import calculate_kpis
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.cross_bank.matcher import CrossBankMatcher
from finzanjir_ai.knowledge.index import KnowledgeIndex, build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.pipeline import process_transaction


@dataclass(frozen=True)
class SystemFlow:
    """The executable prototype path behind the separate UI windows."""

    window_ids: tuple[str, ...]
    transitions: tuple[tuple[str, str], ...]
    architecture_layers: int = 16

    def execute(self, transaction: dict[str, Any], *, knowledge_index: KnowledgeIndex) -> dict[str, Any]:
        if not isinstance(transaction, dict):
            raise ValueError("transaction must be an object")
        if transaction.get("synthetic") is not True:
            raise ValueError("Unified prototype flow accepts only explicitly synthetic transactions")

        pipeline = process_transaction(
            transaction,
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )

        cross_bank_authorized = transaction.get("cross_bank_authorized", False)
        if not isinstance(cross_bank_authorized, bool):
            raise ValueError("cross_bank_authorized must be boolean")
        if cross_bank_authorized and transaction.get("synthetic") is True:
            raise ValueError("synthetic transactions cannot authorize cross-bank exchange")
        has_cross_bank_keys = any(
            isinstance(transaction.get(key), str) and transaction.get(key, "").strip()
            for key in ("device_id", "network_id")
        )
        shadow_only_multi_signal = (
            transaction.get("signal_events") is not None
            and transaction.get("shadow_mode", True) is True
        )
        if has_cross_bank_keys and not cross_bank_authorized and not shadow_only_multi_signal:
            raise ValueError("authorized cross-bank exchange is required")

        if pipeline.signal is None or pipeline.risk is None or pipeline.case is None:
            ai = FINZANJIRAI(knowledge_index).answer(
                "Why was no case opened?",
                runtime_refs=(transaction["transaction_id"],),
                working_memory_scope=transaction["transaction_id"],
            )
            return {
                "transaction_id": transaction["transaction_id"],
                "pipeline": pipeline,
                "case": None,
                "decision": None,
                "bank_status": None,
                "cross_bank": CrossBankMatcher().match(
                    [],
                    scope="cross_bank",
                    authorized_exchange=True,
                ),
                "audit": (),
                "ai": ai,
                "citizen_status": {
                    "case_id": None,
                    "status": "SHADOW_ONLY" if pipeline.risk and pipeline.risk.get("shadow_mode") else "NO_CASE",
                    "message": "Shadow Mode: natija qayd etildi, real to‘lov yoki bank qaroriga ta’sir qilmaydi." if pipeline.risk and pipeline.risk.get("shadow_mode") else "Hodisa bo‘yicha Case ochilmadi.",
                },
                "kpi": calculate_kpis(
                    signals_detected=len(pipeline.signals),
                    cases_opened=0,
                    cases_actioned=0,
                    review_seconds_total=0,
                    data_mode="synthetic",
                ),
                "layers_16": self._layer_trace(transaction_id=transaction["transaction_id"]),
            }

        cross_bank = CrossBankMatcher().match(
            [
                {
                    "transaction_id": transaction["transaction_id"],
                    "bank_id": transaction["bank_id"],
                    "device_id": transaction.get("device_id", ""),
                    "network_id": transaction.get("network_id", ""),
                },
                {
                    "transaction_id": f"{transaction['transaction_id']}-peer",
                    "bank_id": "bank-b",
                    "device_id": transaction.get("device_id", ""),
                    "network_id": transaction.get("network_id", ""),
                },
            ],
            scope="cross_bank",
            authorized_exchange=cross_bank_authorized or not has_cross_bank_keys,
        )

        manager = CaseManager()
        case = manager.open_case(
            case_id=pipeline.case["id"],
            signal_ids=pipeline.case["signal_ids"],
            risk_id=pipeline.case["risk_id"],
            threshold_id=pipeline.case["threshold_id"],
            transaction_id=transaction["transaction_id"],
            escalation_met=bool(pipeline.risk["threshold_met"]),
        )
        decision = manager.apply_human_decision(
            case_id=case["case_id"],
            actor_id="demo-reviewer",
            decision="APPROVE_ACTION",
            reason="Synthetic demo evidence supports continued review.",
            decision_origin="synthetic_demo",
            actor_type="synthetic_demo",
            is_authoritative=False,
        )

        runtime_refs = tuple(
            value
            for value in (
                transaction["transaction_id"],
                pipeline.signal["id"],
                pipeline.evidence["id"] if pipeline.evidence else None,
                pipeline.risk["id"],
                case["case_id"],
                decision["human_decision"]["decision_id"],
                decision["audit_event"]["audit_id"],
                *(match["correlation_key_hash"] for match in cross_bank.matches),
            )
            if value
        )
        ai = FINZANJIRAI(knowledge_index).answer(
            "Why does case escalation require evidence?",
            runtime_refs=runtime_refs,
            working_memory_scope=case["case_id"],
        )

        return {
            "transaction_id": transaction["transaction_id"],
            "pipeline": pipeline,
            "case": case,
            "decision": decision,
            "bank_status": decision["bank_status"],
            "cross_bank": cross_bank,
            "audit": (decision["audit_event"],),
            "ai": ai,
            "citizen_status": decision["citizen_status"],
            "kpi": calculate_kpis(
                signals_detected=1,
                cases_opened=1,
                cases_actioned=0,
                review_seconds_total=0,
                data_mode="synthetic",
            ),
            "layers_16": self._layer_trace(transaction_id=transaction["transaction_id"]),
        }

    def explain_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Return a concise, presentation-safe explanation of the executed flow."""
        pipeline = result["pipeline"]
        return {
            "data_mode": "synthetic",
            "stages": [
                {"id": "synthetic_bank", "title": "Synthetic Bank", "purpose": "Sintetik tranzaksiyani qabul qilish va tekshirish."},
                {"id": "signal_risk", "title": "Signal/Risk", "purpose": "Signal, evidence, risk score va thresholdni hisoblash."},
                {"id": "cross_bank_fraud", "title": "Cross-Bank Fraud", "purpose": "Faqat vakolatli scope ichida banklararo bog‘lanishni tekshirish."},
                {"id": "human_case", "title": "Human+Case", "purpose": "Escalation asosida Case ochish va inson ko‘rigini qayd etish."},
                {"id": "audit_kpi", "title": "Audit/KPI", "purpose": "Qaror va tizim izini auditga, natijalarni KPIga uzatish."},
                {"id": "finzanjir_ai", "title": "FINZANJIR AI", "purpose": "Canonical knowledge va runtime refs asosida tushuntirish berish."},
                {"id": "citizen", "title": "Citizen", "purpose": "Vakolatli natijani fuqaro uchun tushunarli statusga aylantirish."},
                {"id": "layers_16", "title": "16 Layers", "purpose": "Butun oqimni 16 qatlam bo‘yicha kuzatish."},
            ],
            "runtime": {
                "transaction_id": result["transaction_id"],
                "signal_id": pipeline.signal["id"] if pipeline.signal else None,
                "evidence_id": pipeline.evidence["id"] if pipeline.evidence else None,
                "risk_id": pipeline.risk["id"] if pipeline.risk else None,
                "case_id": result["case"]["case_id"] if result["case"] else None,
                "risk_level": pipeline.risk["level"] if pipeline.risk else None,
                "case_opened": result["case"] is not None,
                "cross_bank_matches": len(result["cross_bank"].matches),
                "layers_covered": len(result["layers_16"]),
            },
            "explanation": {
                "signal_is_not_fraud_proof": True,
                "risk_is_not_guilt": True,
                "case_is_not_guilt": True,
                "ai_is_not_final_decision_maker": True,
                "synthetic_data_only": True,
            },
        }

    def trace(self, transaction_id: str) -> list[dict[str, Any]]:
        return [
            {
                "sequence": index + 1,
                "window_id": window_id,
                "transaction_id": transaction_id,
                "architecture_layers": self.architecture_layers,
                "data_mode": "synthetic",
            }
            for index, window_id in enumerate(self.window_ids)
        ]

    def _layer_trace(self, *, transaction_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "layer_id": f"layer_{index:02d}",
                "transaction_id": transaction_id,
                "status": "covered",
            }
            for index in range(1, self.architecture_layers + 1)
        )

    @staticmethod
    def demo_knowledge_index() -> KnowledgeIndex:
        return build_index_from_document(load_canonical_knowledge())


def build_system_flow() -> SystemFlow:
    window_ids = (
        "synthetic_bank",
        "signal_risk",
        "cross_bank_fraud",
        "human_case",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    )
    return SystemFlow(
        window_ids=window_ids,
        transitions=tuple(zip(window_ids, window_ids[1:])),
    )
