from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


def test_system_flow_is_a_real_pipeline_not_only_a_visual_sequence():
    flow = build_system_flow()
    assert flow.window_ids == (
        "synthetic_bank",
        "signal_risk",
        "cross_bank_fraud",
        "human_case",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    )
    assert flow.transitions == tuple(zip(flow.window_ids, flow.window_ids[1:]))


def test_system_flow_keeps_synthetic_decision_non_authoritative():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-FLOW-001",
        "bank_id": "bank-a",
        "actor_id": "actor-flow-001",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(transaction_id="TX-FLOW-001", observed_at="2026-11-11T00:00:00Z"),
        "shadow_mode": False,
    }
    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())

    assert result["transaction_id"] == "TX-FLOW-001"
    assert result["pipeline"].signal["transaction_id"] == "TX-FLOW-001"
    assert result["pipeline"].signal["id"] in result["pipeline"].risk["signal_ids"]
    assert result["case"]["transaction_id"] == "TX-FLOW-001"
    assert result["case"]["status"] == "OPEN"
    assert result["decision"]["case"]["case_id"] == result["case"]["case_id"]
    assert result["decision"]["human_decision"]["is_authoritative"] is False
    assert result["cross_bank"].matches == []
    assert result["audit"]
    assert result["ai"].runtime_context.runtime_refs
    assert result["citizen_status"]["status"] == "SYNTHETIC_REVIEW_ONLY"
    assert result["bank_status"] is None
    assert len(result["layers_16"]) == 16


def test_system_flow_rejects_synthetic_cross_bank_authorization():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-FLOW-002",
        "bank_id": "bank-a",
        "actor_id": "actor-flow-002",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "device_id": "device-2",
        "network_id": "network-2",
        "cross_bank_authorized": True,
    }

    try:
        flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())
    except ValueError as exc:
        assert "synthetic" in str(exc)
        assert "cross-bank" in str(exc)
    else:
        raise AssertionError("synthetic cross-bank authorization must fail closed")


def test_system_flow_rejects_non_object_transactions_before_field_access():
    import pytest

    flow = build_system_flow()

    with pytest.raises(ValueError, match="transaction must be an object"):
        flow.execute([], knowledge_index=flow.demo_knowledge_index())
