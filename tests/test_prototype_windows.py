from finzanjir_ai.prototype.windows import build_window_registry


def test_unified_prototype_exposes_all_required_windows_and_sixteen_layers():
    registry = build_window_registry()
    assert tuple(window.window_id for window in registry.windows) == (
        "dashboard", "citizen", "human_case", "synthetic_bank", "signal_risk",
        "cross_bank_fraud", "audit_kpi", "finzanjir_ai", "layers_16",
    )
    assert len(registry.layers) == 16
    assert registry.shared_event_flow == "Transaction→Signal→Evidence→Risk→Threshold→Case→HumanDecision→Audit/KPI→AI"
    assert registry.cross_bank_scope == "separate_access_boundary"
