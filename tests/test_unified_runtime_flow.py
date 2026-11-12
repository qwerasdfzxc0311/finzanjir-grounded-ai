from finzanjir_ai.prototype.flow import build_system_flow


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


def test_system_flow_executes_one_transaction_through_all_runtime_stages():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-FLOW-001",
        "bank_id": "bank-a",
        "actor_id": "actor-flow-001",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "device_id": "device-1",
        "network_id": "network-1",
        "cross_bank_authorized": True,
    }
    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())

    assert result["transaction_id"] == "TX-FLOW-001"
    assert result["pipeline"].signal["transaction_id"] == "TX-FLOW-001"
    assert result["pipeline"].risk["signal_id"] == result["pipeline"].signal["id"]
    assert result["case"]["transaction_id"] == "TX-FLOW-001"
    assert result["decision"]["case"]["case_id"] == result["case"]["case_id"]
    assert result["cross_bank"].matches
    assert result["audit"]
    assert result["ai"].runtime_context.runtime_refs
    assert result["citizen_status"]["case_id"] == result["case"]["case_id"]
    assert len(result["layers_16"]) == 16


def test_system_flow_keeps_cross_bank_authorization_explicit():
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
    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())
    assert all(match["scope"] == "cross_bank" for match in result["cross_bank"].matches)
