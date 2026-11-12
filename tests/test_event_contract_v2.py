import json
import pytest
from pathlib import Path

from finzanjir_ai.audit.service import AuditLog
from finzanjir_ai.case.manager import CaseManager
from finzanjir_ai.risk.pipeline import process_transaction


ROOT = Path(__file__).resolve().parents[1]


def test_event_contract_v2_and_envelope_required_fields_match():
    contracts = json.loads((ROOT / "contracts" / "event_contracts_v2.json").read_text(encoding="utf-8"))
    envelope = json.loads((ROOT / "contracts" / "event_envelope_v2.json").read_text(encoding="utf-8"))
    migration = json.loads((ROOT / "contracts" / "contract_migration_v1_to_v2.json").read_text(encoding="utf-8"))

    assert contracts["schema_version"] == "2.0"
    assert contracts["event_envelope"] == "event_envelope_v2.json"
    assert contracts["schemas"]["AuditEvent"]["required"][:-1] == envelope["required"]
    assert contracts["schemas"]["AuditEvent"]["required"][-1] == "data_mode"
    assert migration["preserved_v1_files"] == [
        "contracts/event_contracts_v1.json",
        "contracts/event_envelope_v1.json",
    ]


def test_audit_log_emits_v2_envelope_and_keeps_v1_aliases():
    audit = AuditLog()
    event = audit.append(
        actor_id="reviewer-test",
        event_type="RiskEvaluated",
        object_type="Risk",
        object_id="risk-1",
        source="risk-engine-test",
        scope="bank_internal",
        correlation_id="transaction-1",
        data_mode="synthetic",
        details={"score": 80},
    )

    required = {
        "event_id", "event_type", "occurred_at", "actor_id", "source",
        "scope", "object_type", "object_id", "correlation_id",
        "causation_id", "payload", "data_mode",
    }
    assert required.issubset(event)
    assert event["event_id"] == event["audit_id"]
    assert event["payload"] == event["details"] == {"score": 80}
    assert event["correlation_id"] == "transaction-1"
    assert event["scope"] == "bank_internal"


def test_audit_log_rejects_invalid_scope_and_data_mode():
    audit = AuditLog()
    with pytest.raises(ValueError, match="scope"):
        audit.append(
            actor_id="actor", event_type="Test", object_type="Risk",
            object_id="risk-1", details={}, scope="cross_bank_without_auth",
        )
    with pytest.raises(ValueError, match="data_mode"):
        audit.append(
            actor_id="actor", event_type="Test", object_type="Risk",
            object_id="risk-1", details={}, data_mode="unknown-ish",
        )


def test_case_manager_returns_canonical_v2_objects_and_legacy_aliases():
    manager = CaseManager()
    case = manager.open_case(
        case_id="case-v2-1",
        bank_id="bank-test",
        citizen_id="citizen-test",
        signal_ids=["signal-1", "signal-2"],
        risk_id="risk-1",
        threshold_id="threshold-1",
        transaction_id="transaction-1",
        escalation_met=True,
        data_mode="unknown",
    )
    decision = manager.apply_human_decision(
        case_id="case-v2-1",
        actor_id="reviewer-test",
        decision="APPROVE_ACTION",
        reason="Synthetic unit test",
        decision_origin="authorized_human_review",
        actor_type="authorized_human",
        is_authoritative=True,
    )

    assert case["id"] == case["case_id"] == "case-v2-1"
    assert case["signal_ids"] == case["source_signal_ids"] == ["signal-1", "signal-2"]
    assert decision["human_decision"]["id"] == decision["human_decision"]["decision_id"]
    assert decision["bank_status"]["id"] == decision["bank_status"]["status_id"]
    assert decision["bank_status"]["bank_id"] == "bank-test"
    assert decision["bank_status"]["data_mode"] == "unknown"
    assert decision["citizen_status"]["id"] == decision["citizen_status"]["status_id"]
    assert decision["citizen_status"]["citizen_id"] == "citizen-test"
    assert decision["audit_event"]["event_id"] == decision["audit_event"]["audit_id"]
    assert decision["audit_event"]["scope"] == "bank_internal"
    assert decision["audit_event"]["correlation_id"] == "transaction-1"
    assert decision["audit_event"]["payload"]["case_id"] == "case-v2-1"



def test_legacy_and_multi_signal_pipeline_objects_match_v2_required_fields():
    contracts = json.loads((ROOT / "contracts" / "event_contracts_v2.json").read_text(encoding="utf-8"))
    schemas = contracts["schemas"]
    events = [
        {
            "signal_id": "SIG-018", "evidence_id": "ev-auth", "source": "synthetic",
            "observed_at": "2026-11-12T09:00:00Z", "evidence_quality": 1.0, "recency_factor": 1.0,
        },
        {
            "signal_id": "SIG-006", "evidence_id": "ev-device", "source": "synthetic",
            "observed_at": "2026-11-12T09:00:01Z", "evidence_quality": 1.0, "recency_factor": 1.0,
        },
        {
            "signal_id": "SIG-012", "evidence_id": "ev-account", "source": "synthetic",
            "observed_at": "2026-11-12T09:00:02Z", "evidence_quality": 1.0, "recency_factor": 1.0,
        },
        {
            "signal_id": "SIG-004", "evidence_id": "ev-beneficiary", "source": "synthetic",
            "observed_at": "2026-11-12T09:00:03Z", "evidence_quality": 1.0, "recency_factor": 1.0,
        },
        {
            "signal_id": "SIG-002", "evidence_id": "ev-velocity", "source": "synthetic",
            "observed_at": "2026-11-12T09:00:04Z", "evidence_quality": 1.0, "recency_factor": 1.0,
        },
    ]
    transactions = [
        {
            "transaction_id": "legacy-v2", "bank_id": "bank-a", "actor_id": "actor-a",
            "amount": 2500, "occurred_at": "2026-11-12T09:00:00Z", "synthetic": True,
        },
        {
            "transaction_id": "multi-v2", "bank_id": "bank-a", "actor_id": "actor-a",
            "amount": 2500, "occurred_at": "2026-11-12T09:00:00Z", "synthetic": True,
            "signal_events": events, "shadow_mode": False,
        },
    ]

    for transaction in transactions:
        result = process_transaction(
            transaction,
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )
        for signal in result.signals:
            assert set(schemas["Signal"]["required"]).issubset(signal)
        for evidence in result.evidences:
            assert set(schemas["Evidence"]["required"]).issubset(evidence)
        assert set(schemas["Risk"]["required"]).issubset(result.risk)
        assert set(schemas["Case"]["required"]).issubset(result.case)
