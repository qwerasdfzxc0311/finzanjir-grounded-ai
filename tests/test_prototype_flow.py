import pytest

from finzanjir_ai.prototype.flow import build_system_flow
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


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



@pytest.mark.parametrize("shadow_mode", [False, True])
def test_synthetic_flow_never_invokes_cross_bank_matcher_without_explicit_authorization(monkeypatch, shadow_mode):
    def forbidden_match(*_args, **_kwargs):
        raise AssertionError("unauthorized synthetic flow must not invoke the Cross-Bank matcher")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.CrossBankMatcher.match", forbidden_match)
    flow = build_system_flow()
    transaction_id = f"TX-CROSS-BANK-FAIL-CLOSED-{int(shadow_mode)}"
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-cross-bank-boundary",
        "amount": 2500,
        "occurred_at": "2026-11-18T05:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at="2026-11-18T05:00:00Z",
        ),
        "shadow_mode": shadow_mode,
    }
    events = []

    result = flow.execute(
        transaction,
        knowledge_index=flow.demo_knowledge_index(),
        on_stage=events.append,
    )

    assert result["cross_bank_authorized"] is False
    assert result["cross_bank"].matches == []
    assert result["cross_bank"].graph_edges == []
    terminal = [
        event for event in events
        if event["window_id"] == "cross_bank_fraud" and event["status"] != "RUNNING"
    ]
    assert len(terminal) == 1
    assert terminal[0]["status"] == "DISABLED"
    assert terminal[0]["input_refs"] == []
    assert terminal[0]["output_refs"] == []
