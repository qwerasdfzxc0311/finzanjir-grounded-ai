from finzanjir_ai.prototype.flow import build_system_flow


def _events():
    specs = [
        ("SIG-018", "auth"),
        ("SIG-006", "device"),
        ("SIG-012", "account"),
        ("SIG-004", "beneficiary"),
        ("SIG-002", "velocity"),
    ]
    return [
        {
            "signal_id": signal_id,
            "evidence_id": f"threshold-{evidence}",
            "source": "synthetic-threshold-test",
            "observed_at": "2026-11-12T09:00:00Z",
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
        }
        for signal_id, evidence in specs
    ]


def test_unified_flow_uses_active_threshold_version_and_audits_it():
    flow = build_system_flow()
    updated = flow.threshold_manager.update_threshold(
        value=85,
        changed_by="threshold-reviewer",
        reason="Synthetic shadow calibration",
        expected_version=1,
    )

    result = flow.execute(
        {
            "transaction_id": "TX-THRESHOLD-001",
            "bank_id": "bank-a",
            "actor_id": "actor-threshold",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
            "shadow_mode": True,
            "signal_events": _events(),
        },
        knowledge_index=flow.demo_knowledge_index(),
    )

    assert result["pipeline"].risk["score"] == 80
    assert result["pipeline"].risk["threshold_met"] is False
    assert result["pipeline"].risk["case_eligible"] is False
    assert result["pipeline"].risk["threshold_id"] == updated["threshold"]["id"]
    assert result["pipeline"].risk["threshold_version"] == 2
    assert result["threshold"]["value"] == 85
    assert result["case"] is None
    assert result["audit"][0]["details"]["threshold_version"] == 2
    assert updated["threshold"]["id"] in result["ai"].runtime_context.runtime_refs
