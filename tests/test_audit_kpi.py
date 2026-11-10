from finzanjir_ai.audit.service import AuditLog, calculate_kpis


def test_audit_log_is_append_only_and_traceable():
    audit = AuditLog()
    audit.append(actor_id="reviewer-1", event_type="HumanDecisionApplied", object_type="HumanDecision", object_id="decision-1", details={"decision": "APPROVE_ACTION"})
    events = audit.events()
    assert len(events) == 1
    assert events[0]["actor_id"] == "reviewer-1"
    assert events[0]["object_id"] == "decision-1"
    assert events[0]["details"]["decision"] == "APPROVE_ACTION"


def test_kpis_are_marked_as_synthetic_demo_metrics():
    result = calculate_kpis(
        signals_detected=10,
        cases_opened=4,
        cases_actioned=3,
        review_seconds_total=1200,
        data_mode="synthetic",
    )
    assert result["data_mode"] == "synthetic"
    assert result["signal_to_case_rate"] == 0.4
    assert result["case_action_rate"] == 0.75
    assert result["average_review_seconds"] == 400
