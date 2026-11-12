import pytest

from finzanjir_ai.incident_response import IncidentResponse


def _open(response: IncidentResponse, incident_id: str = "INC-1") -> dict:
    return response.open_incident(
        incident_id=incident_id,
        classification="security",
        severity="high",
        owner="security-reviewer",
        next_step="triage incident",
        evidence=["log-123"],
    )


def test_incident_records_classification_owner_severity_and_evidence():
    response = IncidentResponse()
    incident = _open(response)

    assert incident["incident_id"] == "INC-1"
    assert incident["classification"] == "security"
    assert incident["severity"] == "high"
    assert incident["owner"] == "security-reviewer"
    assert incident["evidence"] == ["log-123"]
    assert incident["status"] == "OPEN"
    assert incident["escalation_required"] is True
    assert incident["timeline"][0]["event"] == "OPENED"


def test_incident_lifecycle_requires_ordered_containment_and_verified_recovery():
    response = IncidentResponse()
    _open(response)

    with pytest.raises(ValueError, match="not allowed"):
        response.record_action(
            "INC-1", action="RECOVERY_STARTED", actor="ops", note="start recovery"
        )

    triaged = response.record_action(
        "INC-1", action="TRIAGED", actor="security-reviewer", note="severity confirmed"
    )
    assert triaged["status"] == "TRIAGED"

    contained = response.record_action(
        "INC-1", action="CONTAINED", actor="security-reviewer",
        note="synthetic test environment isolated", evidence=["containment-log"],
    )
    assert contained["status"] == "CONTAINED"

    recovering = response.record_action(
        "INC-1", action="RECOVERY_STARTED", actor="ops", note="restore test service"
    )
    assert recovering["status"] == "RECOVERING"

    with pytest.raises(ValueError, match="requires evidence"):
        response.record_action(
            "INC-1", action="RECOVERY_VERIFIED", actor="ops", note="recovery check"
        )

    recovered = response.record_action(
        "INC-1", action="RECOVERY_VERIFIED", actor="reviewer",
        note="health checks passed", evidence=["health-check-run-1"],
    )
    assert recovered["status"] == "RECOVERED"
    assert "health-check-run-1" in recovered["evidence"]


def test_incident_cannot_close_before_recovery_is_verified():
    response = IncidentResponse()
    _open(response)

    result = response.close_incident("INC-1", recovery_verified=True)

    assert result["closed"] is False
    assert result["reason"] == "recovery_not_verified"
    assert result["status"] == "OPEN"
    assert response.get_incident("INC-1")["status"] == "OPEN"


def test_incident_closes_only_after_recovery_and_retains_timeline():
    response = IncidentResponse()
    _open(response)
    response.record_action("INC-1", action="CONTAINED", actor="ops", note="isolated")
    response.record_action("INC-1", action="RECOVERY_STARTED", actor="ops", note="restore")
    response.record_action(
        "INC-1", action="RECOVERY_VERIFIED", actor="reviewer",
        note="verified", evidence=["recovery-evidence"],
    )

    result = response.close_incident("INC-1", recovery_verified=True)

    assert result["closed"] is True
    assert result["status"] == "CLOSED"
    assert [item["event"] for item in result["timeline"]][-1] == "CLOSED"
    assert response.get_incident("INC-1")["status"] == "CLOSED"


def test_incident_rejects_invalid_fields_and_duplicate_ids_without_mutation():
    response = IncidentResponse()
    with pytest.raises(ValueError, match="severity"):
        response.open_incident(
            incident_id="INC-BAD", classification="security", severity="urgent",
            owner="ops", next_step="triage",
        )
    _open(response)
    with pytest.raises(ValueError, match="already exists"):
        _open(response)
    with pytest.raises(ValueError, match="evidence"):
        response.record_action(
            "INC-1", action="CONTAINED", actor="ops", note="bad evidence", evidence=["", 3]
        )
    assert response.get_incident("INC-1")["status"] == "OPEN"
