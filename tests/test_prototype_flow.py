from finzanjir_ai.prototype.flow import build_system_flow


def test_prototype_flow_connects_all_windows_in_order():
    flow = build_system_flow()
    assert flow.window_ids == (
        "synthetic_bank",
        "signal_risk",
        "human_case",
        "cross_bank_fraud",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    )
    assert flow.transitions == (
        ("synthetic_bank", "signal_risk"),
        ("signal_risk", "human_case"),
        ("human_case", "cross_bank_fraud"),
        ("cross_bank_fraud", "audit_kpi"),
        ("audit_kpi", "finzanjir_ai"),
        ("finzanjir_ai", "citizen"),
        ("citizen", "layers_16"),
    )


def test_prototype_flow_preserves_shared_transaction_identity():
    flow = build_system_flow()
    trace = flow.trace("TX-DEMO-001")
    assert trace[0]["transaction_id"] == "TX-DEMO-001"
    assert all(step["transaction_id"] == "TX-DEMO-001" for step in trace)
    assert trace[-1]["architecture_layers"] == 16


def test_prototype_flow_keeps_cross_bank_as_explicit_boundary():
    flow = build_system_flow()
    trace = flow.trace("TX-DEMO-001")
    cross_bank = next(step for step in trace if step["window_id"] == "cross_bank_fraud")
    assert cross_bank["scope"] == "cross_bank"
    assert cross_bank["authorized_exchange"] is True
