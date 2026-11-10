import pytest

from finzanjir_ai.contracts.event_validation import (
    build_event_envelope,
    validate_event_envelope,
    validate_object,
)


def test_valid_case_event_envelope_is_accepted():
    envelope = build_event_envelope(
        event_id="evt-1",
        event_type="CaseOpened",
        occurred_at="2026-11-11T00:00:00Z",
        actor_id="system",
        scope="bank_internal",
        object_type="Case",
        object_id="case-1",
        payload={"status": "OPEN"},
    )

    assert validate_event_envelope(envelope) is None


def test_event_envelope_rejects_missing_scope():
    envelope = {
        "event_id": "evt-1",
        "event_type": "CaseOpened",
        "occurred_at": "2026-11-11T00:00:00Z",
        "actor_id": "system",
        "object_type": "Case",
        "object_id": "case-1",
        "payload": {"status": "OPEN"},
    }

    with pytest.raises(ValueError, match="scope"):
        validate_event_envelope(envelope)


def test_case_rejects_unknown_status():
    case = {
        "id": "case-1",
        "signal_ids": ["sig-1"],
        "risk_id": "risk-1",
        "threshold_id": "thr-1",
        "status": "UNKNOWN",
        "opened_at": "2026-11-11T00:00:00Z",
    }

    with pytest.raises(ValueError, match="status"):
        validate_object("Case", case)
