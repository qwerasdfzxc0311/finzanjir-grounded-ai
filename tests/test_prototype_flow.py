from finzanjir_ai.prototype.flow import build_system_flow


def test_prototype_flow_connects_all_windows_in_order():
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


def test_prototype_flow_preserves_shared_transaction_identity():
    flow = build_system_flow()
    trace = flow.trace("TX-DEMO-001")
    assert trace[0]["transaction_id"] == "TX-DEMO-001"
    assert all(step["transaction_id"] == "TX-DEMO-001" for step in trace)
    assert trace[-1]["architecture_layers"] == 16
    assert trace[-1]["window_id"] == "layers_16"


def test_prototype_flow_keeps_cross_bank_as_explicit_boundary():
    flow = build_system_flow()
    assert "cross_bank_fraud" in flow.window_ids
    cross_bank_index = flow.window_ids.index("cross_bank_fraud")
    assert flow.transitions[cross_bank_index - 1][1] == "cross_bank_fraud"
    assert flow.transitions[cross_bank_index][0] == "cross_bank_fraud"
