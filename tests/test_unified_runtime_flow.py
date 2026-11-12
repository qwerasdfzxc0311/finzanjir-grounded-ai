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
    assert {item["status"] for item in result["layers_16"]} == {"PARTIAL"}
    assert result["layers_16"][0]["evidence_refs"]
    assert flow.layer_status_summary() == {"total": 16, "complete": 0, "partial": 16, "planned": 0}


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



def test_window_execution_trace_reports_actual_status_for_shadow_and_review_paths():
    flow = build_system_flow()
    for shadow_mode in (True, False):
        transaction_id = "TX-WINDOW-STATUS-" + ("SHADOW" if shadow_mode else "REVIEW")
        transaction = {
            "transaction_id": transaction_id,
            "bank_id": "bank-synthetic",
            "actor_id": "actor-window-status",
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
        trace = flow.build_window_trace(result)
        by_window = {item["window_id"]: item for item in trace}

        assert [item["window_id"] for item in trace] == list(flow.window_ids)
        assert all(item["transaction_id"] == transaction_id for item in trace)
        assert all(item["data_mode"] == "synthetic" for item in trace)
        assert by_window["synthetic_bank"]["status"] == "COMPLETED"
        assert by_window["signal_risk"]["status"] == "COMPLETED"
        assert by_window["cross_bank_fraud"]["status"] == "DISABLED"
        assert by_window["cross_bank_fraud"]["output_refs"] == []
        assert by_window["audit_kpi"]["status"] == "COMPLETED"
        assert by_window["finzanjir_ai"]["status"] in {"COMPLETED", "ABSTAINED"}
        assert by_window["citizen"]["status"] == "SYNTHETIC_STATUS_ONLY"
        assert by_window["layers_16"]["status"] == "PARTIAL"
        assert len(by_window["layers_16"]["output_refs"]) == 16

        if shadow_mode:
            assert by_window["human_case"]["status"] == "SHADOW_ONLY"
            assert by_window["human_case"]["output_refs"] == []
        else:
            assert by_window["human_case"]["status"] == "SYNTHETIC_REVIEW_ONLY"
            assert result["case"]["case_id"] in by_window["human_case"]["output_refs"]



def test_all_window_references_form_one_consistent_synthetic_transaction_chain():
    flow = build_system_flow()
    transaction_id = "TX-CROSS-WINDOW-REFS-001"
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-cross-window-refs",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at="2026-11-12T09:00:00Z",
        ),
        "shadow_mode": False,
    }

    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())
    trace = flow.build_window_trace(result)
    by_id = {item["window_id"]: item for item in trace}
    pipeline = result["pipeline"]
    signal_ids = {item["id"] for item in pipeline.signals}
    evidence_ids = {item["id"] for item in pipeline.evidences}
    risk_id = pipeline.risk["id"]
    case_id = result["case"]["case_id"]
    decision_id = result["decision"]["human_decision"]["decision_id"]
    audit_ids = {item["event_id"] for item in result["audit"]}
    layer_ids = {item["layer_id"] for item in result["layers_16"]}

    assert len(trace) == 8
    assert [item["sequence"] for item in trace] == list(range(1, 9))
    assert all(item["transaction_id"] == transaction_id for item in trace)
    assert all(item["data_mode"] == "synthetic" for item in trace)

    assert transaction_id in by_id["synthetic_bank"]["output_refs"]
    assert transaction_id in by_id["signal_risk"]["input_refs"]
    assert signal_ids | evidence_ids | {risk_id} <= set(by_id["signal_risk"]["output_refs"])

    # Cross-bank is deliberately disabled in this public synthetic flow.
    assert by_id["cross_bank_fraud"]["status"] == "DISABLED"
    assert by_id["cross_bank_fraud"]["input_refs"] == []
    assert by_id["cross_bank_fraud"]["output_refs"] == []

    assert risk_id in by_id["human_case"]["input_refs"]
    assert {case_id, decision_id} <= set(by_id["human_case"]["output_refs"])
    assert transaction_id in by_id["audit_kpi"]["input_refs"]
    assert audit_ids <= set(by_id["audit_kpi"]["output_refs"])

    ai_refs = set(by_id["finzanjir_ai"]["input_refs"])
    assert {transaction_id, risk_id} | signal_ids | evidence_ids <= ai_refs

    assert decision_id in by_id["citizen"]["input_refs"]
    assert result["citizen_status"]["status"] == "SYNTHETIC_REVIEW_ONLY"
    assert case_id in by_id["citizen"]["output_refs"]
    assert transaction_id in by_id["layers_16"]["input_refs"]
    assert layer_ids <= set(by_id["layers_16"]["output_refs"])



def test_flow_emits_real_ordered_stage_callbacks_for_synthetic_review():
    flow = build_system_flow()
    transaction_id = "TX-LIVE-PROGRESS-001"
    events = []
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-live-progress",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at="2026-11-12T09:00:00Z",
        ),
        "shadow_mode": False,
    }

    result = flow.execute(
        transaction,
        knowledge_index=flow.demo_knowledge_index(),
        on_stage=events.append,
    )

    assert result["transaction_id"] == transaction_id
    assert [event["window_id"] for event in events] == [
        window_id
        for window_id in flow.window_ids
        for _ in range(2)
    ]
    assert [event["status"] for event in events[::2]] == ["RUNNING"] * 8
    assert [event["status"] for event in events[1::2]] == [
        "COMPLETED",
        "COMPLETED",
        "DISABLED",
        "SYNTHETIC_REVIEW_ONLY",
        "COMPLETED",
        "COMPLETED",
        "SYNTHETIC_STATUS_ONLY",
        "PARTIAL",
    ]
    assert all(event["transaction_id"] == transaction_id for event in events)
    assert all(event["data_mode"] == "synthetic" for event in events)


def test_progress_callback_failure_does_not_change_flow_result():
    flow = build_system_flow()
    transaction_id = "TX-PROGRESS-CALLBACK-FAIL-001"
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-progress-fail",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at="2026-11-12T09:00:00Z",
        ),
        "shadow_mode": True,
    }

    def broken_transport(_event):
        raise RuntimeError("synthetic progress transport failure")

    result = flow.execute(
        transaction,
        knowledge_index=flow.demo_knowledge_index(),
        on_stage=broken_transport,
    )

    assert result["transaction_id"] == transaction_id
    assert result["pipeline"].risk is not None



@pytest.mark.parametrize("shadow_mode", [False, True])
def test_window_trace_inputs_only_reference_outputs_from_prior_windows(shadow_mode):
    flow = build_system_flow()
    transaction_id = f"TX-TRACE-CLOSURE-{'SHADOW' if shadow_mode else 'CASE'}"
    transaction = {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-trace-closure",
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
    trace = flow.build_window_trace(result)
    available_refs = set()

    assert len(trace) == len(flow.window_ids) == 8
    for stage in trace:
        inputs = stage["input_refs"]
        outputs = stage["output_refs"]
        assert all(isinstance(ref, str) and ref for ref in inputs + outputs)
        assert set(inputs) <= available_refs, (
            f"{stage['window_id']} references data not emitted by an earlier window: "
            f"{sorted(set(inputs) - available_refs)}"
        )
        assert len(outputs) == len(set(outputs)), f"{stage['window_id']} emits duplicate refs"
        available_refs.update(outputs)
