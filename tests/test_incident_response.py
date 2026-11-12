from finzanjir_ai.incident_response import IncidentResponse


def test_incident_records_classification_and_owner():
    incident = IncidentResponse().open_incident(
        incident_id="INC-1",
        classification="security",
        severity="high",
        owner="security-reviewer",
        next_step="contain and investigate",
    )

    assert incident["incident_id"] == "INC-1"
    assert incident["classification"] == "security"
    assert incident["severity"] == "high"
    assert incident["owner"] == "security-reviewer"
    assert incident["next_step"] == "contain and investigate"


def test_incident_preserves_evidence_references_and_timeline():
    incident = IncidentResponse().open_incident(
        incident_id="INC-2",
        classification="data_exposure",
        severity="critical",
        owner="security-reviewer",
        next_step="preserve evidence",
        evidence=["log-123", "case-456"],
    )

    assert incident["evidence"] == ["log-123", "case-456"]
    assert incident["timeline"]


def test_incident_escalates_when_severity_is_critical():
    incident = IncidentResponse().open_incident(
        incident_id="INC-3",
        classification="security",
        severity="critical",
        owner="security-reviewer",
        next_step="escalate",
    )

    assert incident["escalation_required"] is True


def test_incident_cannot_be_silently_closed_without_recovery_record():
    response = IncidentResponse()

    result = response.close_incident("INC-4", recovery_verified=False)

    assert result["closed"] is False
    assert result["reason"] == "recovery_not_verified"
    assert result["incident_retained"] is True
