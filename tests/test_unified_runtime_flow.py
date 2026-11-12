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
    assert {item["status"] for item in result["layers_16"]} == {"PARTIAL", "PLANNED"}
    assert result["layers_16"][0]["evidence_refs"]
    assert flow.layer_status_summary() == {"total": 16, "complete": 0, "partial": 12, "planned": 4}


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



import pytest


@pytest.mark.parametrize("shadow_mode", [True, False], ids=["shadow", "synthetic-review"])
def test_all_window_outputs_share_one_synthetic_transaction_correlation(shadow_mode):
    flow = build_system_flow()
    transaction_id = "TX-WINDOW-CORRELATION-" + ("SHADOW" if shadow_mode else "REVIEW")
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-synthetic-window-test",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at="2026-11-12T09:00:00Z",
        ),
        "shadow_mode": shadow_mode,
    }

    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())
    trace = flow.trace(transaction_id)

    assert result["transaction_id"] == transaction_id
    assert [item["window_id"] for item in trace] == list(flow.window_ids)
    assert all(item["transaction_id"] == transaction_id for item in trace)
    assert all(item["data_mode"] == "synthetic" for item in trace)

    pipeline = result["pipeline"]
    risk = pipeline.risk
    assert pipeline.signal["transaction_id"] == transaction_id
    assert all(signal["id"] in risk["signal_ids"] for signal in pipeline.signals)
    assert {item["evidence_id"] for item in risk["contributions"]} == {
        item["id"] for item in pipeline.evidences
    }

    assert result["cross_bank"].matches == []
    assert result["audit"]
    assert all(item["correlation_id"] == transaction_id for item in result["audit"])
    assert result["ai"].runtime_context.runtime_refs
    assert transaction_id in result["ai"].runtime_context.runtime_refs
    assert risk["id"] in result["ai"].runtime_context.runtime_refs
    assert all(item["id"] in result["ai"].runtime_context.runtime_refs for item in pipeline.signals)
    assert all(item["id"] in result["ai"].runtime_context.runtime_refs for item in pipeline.evidences)

    assert len(result["layers_16"]) == 16
    assert all(item["transaction_id"] == transaction_id for item in result["layers_16"])
    assert result["kpi"]["data_mode"] == "synthetic"

    if shadow_mode:
        assert result["case"] is None
        assert result["decision"] is None
        assert result["citizen_status"]["status"] == "SHADOW_ONLY"
        assert result["kpi"]["signal_to_case_rate"] == 0
    else:
        assert result["case"]["transaction_id"] == transaction_id
        assert result["decision"]["case"]["case_id"] == result["case"]["case_id"]
        assert result["decision"]["human_decision"]["is_authoritative"] is False
        assert result["citizen_status"]["status"] == "SYNTHETIC_REVIEW_ONLY"
