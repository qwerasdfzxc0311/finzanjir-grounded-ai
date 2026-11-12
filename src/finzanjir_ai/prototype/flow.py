from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from finzanjir_ai.architecture.layers import build_layer_trace, get_layer_status_summary
from finzanjir_ai.audit.service import AuditLog, calculate_kpis
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.cross_bank.matcher import CrossBankMatcher
from finzanjir_ai.knowledge.index import KnowledgeIndex, build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.risk.pipeline import process_transaction
from finzanjir_ai.risk.thresholds import ThresholdManager


@dataclass(frozen=True)
class SystemFlow:
    """The executable prototype path behind the separate UI windows."""

    window_ids: tuple[str, ...]
    transitions: tuple[tuple[str, str], ...]
    architecture_layers: int = 16
    threshold_manager: ThresholdManager = field(default_factory=ThresholdManager, compare=False, repr=False)

    def execute(
        self,
        transaction: dict[str, Any],
        *,
        knowledge_index: KnowledgeIndex,
        on_stage: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(transaction, dict):
            raise ValueError("transaction must be an object")
        if transaction.get("synthetic") is not True:
            raise ValueError("Unified prototype flow accepts only explicitly synthetic transactions")

        transaction_id = transaction.get("transaction_id", "")
        def emit(window_id: str, status: str, summary: str, input_refs: tuple[str, ...] = (), output_refs: tuple[str, ...] = ()) -> None:
            if on_stage is None:
                return
            event = {
                "sequence": self.window_ids.index(window_id) + 1,
                "window_id": window_id,
                "transaction_id": transaction_id,
                "data_mode": "synthetic",
                "status": status,
                "summary": summary,
                "input_refs": list(input_refs),
                "output_refs": list(output_refs),
            }
            try:
                on_stage(event)
            except Exception:
                # Progress transport must never change the underlying risk-flow result.
                return

        emit("synthetic_bank", "RUNNING", "Sintetik tranzaksiya tekshirilmoqda.")
        emit("synthetic_bank", "COMPLETED", "Sintetik tranzaksiya yagona oqimga qabul qilindi.", output_refs=(transaction_id,))

        emit("signal_risk", "RUNNING", "Signal va risk tahlili bajarilmoqda.", input_refs=(transaction_id,))
        threshold_config = self.threshold_manager.get_active()
        pipeline = process_transaction(
            transaction,
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
            threshold_config=threshold_config,
        )

        emit(
            "signal_risk",
            "COMPLETED" if pipeline.risk else "NOT_RUN",
            "Signal, dalil va risk natijasi tayyor." if pipeline.risk else "Risk natijasi hosil bo‘lmadi.",
            input_refs=(transaction_id,),
            output_refs=tuple(
                [item["id"] for item in pipeline.signals]
                + [item["id"] for item in pipeline.evidences]
                + ([pipeline.risk["id"]] if pipeline.risk and pipeline.risk.get("id") else [])
                + ([pipeline.risk["threshold_id"]] if pipeline.risk and pipeline.risk.get("threshold_id") else [])
            ),
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
            (transaction.get("signal_events") is not None or transaction.get("signal_observations") is not None)
            and transaction.get("shadow_mode", True) is True
        )
        if has_cross_bank_keys and not cross_bank_authorized and not shadow_only_multi_signal:
            raise ValueError("authorized cross-bank exchange is required")

        if pipeline.signal is None or pipeline.risk is None or pipeline.case is None:
            emit("cross_bank_fraud", "RUNNING", "Cross-Bank ruxsat chegarasi tekshirilmoqda.")
            shadow_cross_bank = CrossBankMatcher().match([], scope="cross_bank", authorized_exchange=True)
            emit("cross_bank_fraud", "DISABLED", "Banklararo almashinuv o‘chiq; bu moslik topilmadi degani emas.")
            emit("human_case", "RUNNING", "Case ochish mezonlari va Shadow Mode tekshirilmoqda.", input_refs=(pipeline.risk["id"],) if pipeline.risk else ())
            human_status = "SHADOW_ONLY" if pipeline.risk and pipeline.risk.get("shadow_mode") else "NOT_ELIGIBLE"
            emit("human_case", human_status, "Shadow Mode yoki Case mezonlari sabab Case ochilmadi.")
            shadow_runtime_refs = tuple(
                value
                for value in (
                    transaction["transaction_id"],
                    *(item["id"] for item in pipeline.signals),
                    *(item["id"] for item in pipeline.evidences),
                    pipeline.risk["id"] if pipeline.risk else None,
                    pipeline.risk.get("threshold_id") if pipeline.risk else None,
                )
                if value
            )
            emit("audit_kpi", "RUNNING", "Audit va sintetik KPI tayyorlanmoqda.", input_refs=(transaction_id,))
            shadow_audit = None
            if pipeline.risk is not None:
                is_shadow = pipeline.risk.get("shadow_mode") is True
                shadow_audit = AuditLog().append(
                    actor_id="system:synthetic-shadow" if is_shadow else "system:synthetic-review",
                    event_type="RISK_EVALUATED_SHADOW" if is_shadow else "RISK_EVALUATED_NO_CASE",
                    object_type="Risk",
                    object_id=pipeline.risk["id"],
                    source="risk_engine",
                    scope="bank_internal",
                    correlation_id=transaction["transaction_id"],
                    data_mode="synthetic",
                    details={
                        "score": pipeline.risk["score"],
                        "risk_level": pipeline.risk["level"],
                        "signal_ids": pipeline.risk["signal_ids"],
                        "evidence_count": pipeline.risk["evidence_count"],
                        "engine_version": pipeline.risk["engine_version"],
                        "registry_version": pipeline.risk.get("registry_version"),
                        "threshold_id": pipeline.risk.get("threshold_id"),
                        "threshold_version": pipeline.risk.get("threshold_version"),
                        "data_mode": "synthetic",
                        "no_bank_action": True,
                    },
                )
            shadow_kpi = calculate_kpis(
                signals_detected=len(pipeline.signals),
                cases_opened=0,
                cases_actioned=0,
                review_seconds_total=0,
                data_mode="synthetic",
            )
            emit(
                "audit_kpi",
                "COMPLETED",
                "Sintetik audit hodisasi va KPI tayyor.",
                input_refs=(transaction_id,),
                output_refs=(shadow_audit["event_id"],) if shadow_audit else (),
            )
            emit("finzanjir_ai", "RUNNING", "Canonical knowledge va runtime dalillari bilan izoh tayyorlanmoqda.", input_refs=shadow_runtime_refs)
            ai = FINZANJIRAI(knowledge_index).answer(
                "Why was this risk result kept in Shadow Mode?",
                runtime_refs=shadow_runtime_refs,
                working_memory_scope=transaction["transaction_id"],
            )
            ai_answer = getattr(ai, "answer", None)
            emit(
                "finzanjir_ai",
                "ABSTAINED" if getattr(ai_answer, "abstained", False) else "COMPLETED",
                "AI dalil yetishmasligi sabab javobdan tiyildi." if getattr(ai_answer, "abstained", False) else "AI izohi tayyor.",
                input_refs=shadow_runtime_refs,
                output_refs=tuple(getattr(ai_answer, "citations", ()) or ()),
            )
            emit("citizen", "RUNNING", "Sintetik fuqaro statusi tayyorlanmoqda.")
            shadow_citizen_status = {
                "case_id": None,
                "status": "SHADOW_ONLY" if pipeline.risk and pipeline.risk.get("shadow_mode") else "NO_CASE",
                "message": "Shadow Mode: natija qayd etildi, real to‘lov yoki bank qaroriga ta’sir qilmaydi." if pipeline.risk and pipeline.risk.get("shadow_mode") else "Hodisa bo‘yicha Case ochilmadi.",
                "risk_score": pipeline.risk.get("score") if pipeline.risk else None,
                "risk_level": pipeline.risk.get("level") if pipeline.risk else None,
                "case_eligible": pipeline.risk.get("case_eligible", False) if pipeline.risk else False,
            }
            emit("citizen", "SYNTHETIC_STATUS_ONLY", "Faqaro statusi faqat sintetik namuna.")
            emit("layers_16", "RUNNING", "16 qatlam izi shakllantirilmoqda.", input_refs=(transaction_id,))
            shadow_layers = self._layer_trace(transaction_id=transaction_id)
            emit("layers_16", "PARTIAL", "16 qatlam izi tayyor; statuslar qisman/rejalashtirilgan.", input_refs=(transaction_id,), output_refs=tuple(item["layer_id"] for item in shadow_layers))
            return {
                "transaction_id": transaction["transaction_id"],
                "cross_bank_authorized": cross_bank_authorized,
                "pipeline": pipeline,
                "threshold": pipeline.risk.get("threshold") if pipeline.risk else None,
                "case": None,
                "decision": None,
                "bank_status": None,
                "cross_bank": shadow_cross_bank,
                "audit": (shadow_audit,) if shadow_audit else (),
                "ai": ai,
                "citizen_status": shadow_citizen_status,
                "kpi": shadow_kpi,
                "layers_16": shadow_layers,
            }

        emit("cross_bank_fraud", "RUNNING", "Cross-Bank ruxsat chegarasi va moslik tekshirilmoqda.")
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
        emit(
            "cross_bank_fraud",
            "COMPLETED" if cross_bank_authorized else "DISABLED",
            "Vakolatli scope tekshirildi." if cross_bank_authorized else "Banklararo almashinuv o‘chiq.",
            input_refs=(transaction_id,) if cross_bank_authorized else (),
            output_refs=tuple(match["correlation_key_hash"] for match in cross_bank.matches if match.get("correlation_key_hash")),
        )

        emit("human_case", "RUNNING", "Sintetik Case va inson ko‘rigi tayyorlanmoqda.", input_refs=(pipeline.risk["id"],))
        manager = CaseManager()
        case = manager.open_case(
            case_id=pipeline.case["id"],
            signal_ids=pipeline.case["signal_ids"],
            risk_id=pipeline.case["risk_id"],
            threshold_id=pipeline.case["threshold_id"],
            transaction_id=transaction["transaction_id"],
            bank_id=transaction["bank_id"],
            citizen_id=transaction.get("citizen_id", "synthetic-subject"),
            escalation_met=bool(pipeline.risk["threshold_met"]),
            data_mode="synthetic",
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
        emit(
            "human_case",
            "SYNTHETIC_REVIEW_ONLY",
            "Sintetik Case yaratildi; bu rasmiy bank qarori emas.",
            input_refs=(pipeline.risk["id"],),
            output_refs=(case["case_id"], decision["human_decision"]["decision_id"]),
        )

        emit("audit_kpi", "RUNNING", "Audit va KPI natijalari tayyorlanmoqda.", input_refs=(transaction_id,))
        kpi = calculate_kpis(
            signals_detected=len(pipeline.signals),
            cases_opened=1,
            cases_actioned=0,
            review_seconds_total=0,
            data_mode="synthetic",
        )
        audit_event = decision["audit_event"]
        emit("audit_kpi", "COMPLETED", "Audit hodisasi va sintetik KPI tayyor.", input_refs=(transaction_id,), output_refs=tuple(
                ref for ref in (audit_event.get("event_id"), audit_event.get("audit_id")) if ref
            ))

        emit("finzanjir_ai", "RUNNING", "Canonical knowledge va runtime dalillari bilan izoh tayyorlanmoqda.")
        runtime_refs = tuple(
            value
            for value in (
                transaction["transaction_id"],
                *(item["id"] for item in pipeline.signals),
                *(item["id"] for item in pipeline.evidences),
                pipeline.risk["id"],
                pipeline.risk.get("threshold_id"),
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
        ai_answer = getattr(ai, "answer", None)
        emit(
            "finzanjir_ai",
            "ABSTAINED" if getattr(ai_answer, "abstained", False) else "COMPLETED",
            "AI dalil yetishmasligi sabab javobdan tiyildi." if getattr(ai_answer, "abstained", False) else "AI izohi tayyor.",
            input_refs=runtime_refs,
            output_refs=tuple(getattr(ai_answer, "citations", ()) or ()),
        )

        emit("citizen", "RUNNING", "Sintetik fuqaro statusi tayyorlanmoqda.", input_refs=(decision["human_decision"]["decision_id"],))
        citizen_status = decision["citizen_status"] or {
            "case_id": case["case_id"],
            "status": "SYNTHETIC_REVIEW_ONLY",
            "message": "Sintetik sinov natijasi; bankning rasmiy qarori yoki mijozga qo‘llangan chora emas.",
        }
        emit("citizen", "SYNTHETIC_STATUS_ONLY", "Fuqaro oynasi uchun sintetik status tayyor.", input_refs=(decision["human_decision"]["decision_id"],), output_refs=(case["case_id"],))
        emit("layers_16", "RUNNING", "16 qatlam izi shakllantirilmoqda.", input_refs=(transaction_id,))
        layers = self._layer_trace(transaction_id=transaction_id)
        emit("layers_16", "PARTIAL", "16 qatlam izi tayyor; statuslar qisman/rejalashtirilgan.", input_refs=(transaction_id,), output_refs=tuple(item["layer_id"] for item in layers))

        return {
            "transaction_id": transaction["transaction_id"],
            "cross_bank_authorized": cross_bank_authorized,
            "pipeline": pipeline,
            "threshold": pipeline.risk.get("threshold") if pipeline.risk else None,
            "case": case,
            "decision": decision,
            "bank_status": decision["bank_status"],
            "cross_bank": cross_bank,
            "audit": (decision["audit_event"],),
            "ai": ai,
            "citizen_status": citizen_status,
            "kpi": kpi,
            "layers_16": layers,
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
                "signal_ids": [item["id"] for item in pipeline.signals],
                "evidence_id": pipeline.evidence["id"] if pipeline.evidence else None,
                "evidence_ids": [item["id"] for item in pipeline.evidences],
                "risk_id": pipeline.risk["id"] if pipeline.risk else None,
                "case_id": result["case"]["case_id"] if result["case"] else None,
                "risk_level": pipeline.risk["level"] if pipeline.risk else None,
                "risk_score": pipeline.risk.get("score") if pipeline.risk else None,
                "evidence_confidence": pipeline.risk.get("evidence_confidence") if pipeline.risk else None,
                "threshold_id": pipeline.risk.get("threshold_id") if pipeline.risk else None,
                "threshold_version": pipeline.risk.get("threshold_version") if pipeline.risk else None,
                "case_opened": result["case"] is not None,
                "cross_bank_matches": len(result["cross_bank"].matches),
                "layers_traced": len(result["layers_16"]),
                "layer_status_summary": get_layer_status_summary(),
            },
            "explanation": {
                "signal_is_not_fraud_proof": True,
                "risk_is_not_guilt": True,
                "case_is_not_guilt": True,
                "ai_is_not_final_decision_maker": True,
                "synthetic_data_only": True,
            },
        }

    def build_window_trace(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Build truthful post-execution statuses from outputs actually produced."""
        pipeline = result["pipeline"]
        risk = pipeline.risk or {}
        transaction_id = result["transaction_id"]
        signal_ids = [item["id"] for item in pipeline.signals]
        evidence_ids = [item["id"] for item in pipeline.evidences]
        case = result.get("case")
        decision = result.get("decision") or {}
        human_decision = decision.get("human_decision") or {}
        audit_events = list(result.get("audit") or ())
        ai = result.get("ai")
        ai_answer = getattr(ai, "answer", None)
        citizen_status = result.get("citizen_status") or {}
        layers = list(result.get("layers_16") or ())
        layer_counts = {
            "complete": sum(item.get("status") == "COMPLETE" for item in layers),
            "partial": sum(item.get("status") == "PARTIAL" for item in layers),
            "planned": sum(item.get("status") == "PLANNED" for item in layers),
        }
        cross_bank_authorized = result.get("cross_bank_authorized") is True
        cross_bank = result.get("cross_bank")
        cross_bank_matches = list(getattr(cross_bank, "matches", ()) or ())

        stages = [
            {
                "window_id": "synthetic_bank",
                "status": "COMPLETED",
                "status_label": "Bajarildi · sintetik tranzaksiya qabul qilindi",
                "summary": "Sintetik tranzaksiya yagona oqimga qabul qilindi.",
                "input_refs": [],
                "output_refs": [transaction_id],
            },
            {
                "window_id": "signal_risk",
                "status": "COMPLETED" if risk else "NOT_RUN",
                "status_label": "Bajarildi · signal va risk natijasi tayyor" if risk else "Bajarilmadi · risk natijasi yo‘q",
                "summary": "Signal, dalil, ustuvorlik balli va threshold natijasi.",
                "input_refs": [transaction_id],
                "output_refs": [
                    *signal_ids,
                    *evidence_ids,
                    *([risk["id"]] if risk.get("id") else []),
                    *([risk["threshold_id"]] if risk.get("threshold_id") else []),
                ],
            },
            {
                "window_id": "cross_bank_fraud",
                "status": "COMPLETED" if cross_bank_authorized else "DISABLED",
                "status_label": (
                    "Vakolatli scope tekshirildi · moslik bor" if cross_bank_matches
                    else "Vakolatli scope tekshirildi · moslik yo‘q" if cross_bank_authorized
                    else "O‘chiq · banklararo almashinuvga ruxsat yo‘q"
                ),
                "summary": (
                    "Faqat aniq runtime vakolati bo‘lsa cross-bank natijasi ko‘rsatiladi."
                    if cross_bank_authorized
                    else "Banklararo almashinuv bajarilmadi; bu holat moslik topilmadi degani emas."
                ),
                "input_refs": [transaction_id] if cross_bank_authorized else [],
                "output_refs": [
                    item["correlation_key_hash"] for item in cross_bank_matches
                    if item.get("correlation_key_hash")
                ],
            },
            {
                "window_id": "human_case",
                "status": (
                    "SYNTHETIC_REVIEW_ONLY" if case
                    else "SHADOW_ONLY" if risk.get("shadow_mode") is True
                    else "NOT_ELIGIBLE"
                ),
                "status_label": (
                    "Sintetik Case · rasmiy qaror emas" if case
                    else "Shadow Mode · Case ochilmadi" if risk.get("shadow_mode") is True
                    else "Case ochilmadi · mezonlar bajarilmadi"
                ),
                "summary": "Case va inson ko‘rigi faqat sintetik namuna; rasmiy bank qarori emas.",
                "input_refs": [risk["id"]] if risk.get("id") else [],
                "output_refs": [
                    item for item in (
                        case.get("case_id") if case else None,
                        human_decision.get("decision_id"),
                    ) if item
                ],
            },
            {
                "window_id": "audit_kpi",
                "status": "COMPLETED" if audit_events and result.get("kpi") else "PARTIAL",
                "status_label": "Audit va KPI natijasi tayyor" if audit_events and result.get("kpi") else "Qisman · audit yoki KPI natijasi yetishmaydi",
                "summary": "Audit hodisalari va sintetik KPI ko‘rsatkichlari.",
                "input_refs": [transaction_id],
                "output_refs": [
                    ref
                    for item in audit_events
                    for ref in (item.get("event_id"), item.get("audit_id"))
                    if ref
                ],
            },
            {
                "window_id": "finzanjir_ai",
                "status": "ABSTAINED" if getattr(ai_answer, "abstained", False) else "COMPLETED" if ai_answer else "NOT_RUN",
                "status_label": (
                    "AI dalil yetishmasligi sabab javobdan tiyildi"
                    if getattr(ai_answer, "abstained", False)
                    else "AI izohi tayyor" if ai_answer
                    else "AI natijasi mavjud emas"
                ),
                "summary": "AI javobi runtime dalillari va canonical knowledge bilan bog‘langan.",
                "input_refs": list(getattr(getattr(ai, "runtime_context", None), "runtime_refs", ()) or ()),
                "output_refs": list(getattr(ai_answer, "citations", ()) or ()),
            },
            {
                "window_id": "citizen",
                "status": "SYNTHETIC_STATUS_ONLY" if citizen_status else "NOT_AVAILABLE",
                "status_label": (
                    "Sintetik status · fuqaroning haqiqiy bank holati emas"
                    if citizen_status else "Fuqaro statusi mavjud emas"
                ),
                "summary": citizen_status.get("message", "Fuqaro statusi mavjud emas."),
                "input_refs": [human_decision["decision_id"]] if human_decision.get("decision_id") else [],
                "output_refs": [
                    item for item in (
                        citizen_status.get("status_id"),
                        citizen_status.get("case_id"),
                    ) if item
                ],
            },
            {
                "window_id": "layers_16",
                "status": (
                    "COMPLETE" if len(layers) == self.architecture_layers and layer_counts["complete"] == self.architecture_layers
                    else "PARTIAL" if len(layers) == self.architecture_layers
                    else "INCOMPLETE"
                ),
                "status_label": (
                    f"16 qatlam izi · {layer_counts['complete']} to‘liq, {layer_counts['partial']} qisman, {layer_counts['planned']} rejalashtirilgan"
                    if len(layers) == self.architecture_layers
                    else f"Qatlam izi to‘liq emas · {len(layers)} / {self.architecture_layers}"
                ),
                "summary": "Qatlam izi mavjudligi ularning barchasi ishlab chiqilganini anglatmaydi.",
                "input_refs": [transaction_id],
                "output_refs": [item["layer_id"] for item in layers],
            },
        ]
        if [item["window_id"] for item in stages] != list(self.window_ids):
            raise RuntimeError("window execution trace does not match the canonical system flow")
        return [
            {"sequence": index + 1, "transaction_id": transaction_id, "data_mode": "synthetic", **stage}
            for index, stage in enumerate(stages)
        ]

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
        trace = build_layer_trace(transaction_id)
        if len(trace) != self.architecture_layers:
            raise RuntimeError("layer registry count does not match SystemFlow architecture")
        return trace

    @staticmethod
    def layer_status_summary() -> dict[str, int]:
        return get_layer_status_summary()

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
