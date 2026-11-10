import pytest

from finzanjir_ai.contracts.event_validation import validate_event_envelope, validate_object


def test_case_requires_reference_ids_to_be_nonempty_strings():
    case = {
        "id": "case-1",
        "signal_ids": ["sig-1", ""],
        "risk_id": "risk-1",
        "threshold_id": "thr-1",
        "status": "OPEN",
        "opened_at": "2026-11-11T00:00:00Z",
    }

    with pytest.raises(ValueError, match="signal_ids"):
        validate_object("Case", case)


def test_event_object_id_must_match_payload_id():
    envelope = {
        "event_id": "evt-1",
        "event_type": "CaseOpened",
        "occurred_at": "2026-11-11T00:00:00Z",
        "actor_id": "system",
        "scope": "bank_internal",
        "object_type": "Case",
        "object_id": "case-2",
        "payload": {
            "id": "case-1",
            "signal_ids": ["sig-1"],
            "risk_id": "risk-1",
            "threshold_id": "thr-1",
            "status": "OPEN",
            "opened_at": "2026-11-11T00:00:00Z",
        },
    }

    with pytest.raises(ValueError, match="object_id"):
        validate_event_envelope(envelope)
