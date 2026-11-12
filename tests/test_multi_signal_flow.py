from finzanjir_ai.prototype.flow import build_system_flow


def test_multi_signal_flow_connects_case_human_audit_ai_citizen_and_kpi():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-MULTI-FLOW-001",
        "bank_id": "bank-a",
        "actor_id": "actor-multi-flow",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "shadow_mode": False,
        "signal_events": [
            {"signal_id": "SIG-018", "evidence_id": "ev-auth", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:00Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-006", "evidence_id": "ev-device", "source": "synthetic-device", "observed_at": "2026-11-12T08:59:10Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-012", "evidence_id": "ev-account", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:20Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-004", "evidence_id": "ev-beneficiary", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:30Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-002", "evidence_id": "ev-velocity", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:40Z", "evidence_quality": 1.0, "recency_factor": 1.0},
        ],
    }

    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())
    runtime_refs = result["ai"].runtime_context.runtime_refs

    assert result["pipeline"].risk["score"] == 80
    assert result["case"] is not None
    assert len(result["case"]["source_signal_ids"]) == 5
    assert result["decision"]["human_decision"]["is_authoritative"] is False
    assert result["bank_status"] is None
    assert result["citizen_status"]["status"] == "SYNTHETIC_REVIEW_ONLY"
    assert result["audit"][0]["event_type"] == "HumanDecisionApplied"
    assert result["kpi"]["signal_to_case_rate"] == 0.2
    assert all(signal["id"] in runtime_refs for signal in result["pipeline"].signals)
    assert all(evidence["id"] in runtime_refs for evidence in result["pipeline"].evidences)
    assert result["pipeline"].risk["id"] in runtime_refs
