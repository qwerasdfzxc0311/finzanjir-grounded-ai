import pytest

from finzanjir_ai.citizen_appeals import CitizenAppealRegistry


def _submitted(registry: CitizenAppealRegistry, request_type: str = "REVIEW") -> dict:
    return registry.submit(
        case_id="CASE-SYNTHETIC-001",
        citizen_ref="citizen-ref-001",
        request_type=request_type,
        reason="I request a review of this synthetic case.",
        evidence_refs=["evidence-ref-1"],
    )


def test_citizen_can_submit_review_and_correction_requests_without_raw_pii():
    registry = CitizenAppealRegistry()
    review = _submitted(registry, "REVIEW")
    correction = _submitted(registry, "CORRECTION")

    assert review["status"] == "SUBMITTED"
    assert review["data_mode"] == "synthetic"
    assert review["evidence_refs"] == ["evidence-ref-1"]
    assert correction["request_type"] == "CORRECTION"
    assert "account_number" not in review
    assert "phone_number" not in review


def test_appeal_requires_authorized_assigned_reviewer_and_ordered_transitions():
    registry = CitizenAppealRegistry()
    appeal = _submitted(registry)

    with pytest.raises(ValueError, match="authorization"):
        registry.assign_reviewer(
            appeal["appeal_id"], reviewer_ref="reviewer-1", reviewer_authorized=False
        )

    assigned = registry.assign_reviewer(
        appeal["appeal_id"], reviewer_ref="reviewer-1", reviewer_authorized=True
    )
    assert assigned["status"] == "IN_REVIEW"

    with pytest.raises(ValueError, match="assigned reviewer"):
        registry.respond(
            appeal["appeal_id"], reviewer_ref="reviewer-2", outcome="UPHELD",
            response="Reviewed.", reviewer_authorized=True,
        )

    answered = registry.respond(
        appeal["appeal_id"], reviewer_ref="reviewer-1", outcome="UPHELD",
        response="The original review status is maintained.",
        reviewer_authorized=True,
    )
    assert answered["status"] == "RESPONDED"
    assert answered["outcome"] == "UPHELD"


def test_correction_requires_explicit_correction_reference_and_does_not_mutate_case():
    registry = CitizenAppealRegistry()
    appeal = _submitted(registry, "CORRECTION")
    registry.assign_reviewer(
        appeal["appeal_id"], reviewer_ref="reviewer-1", reviewer_authorized=True
    )

    with pytest.raises(ValueError, match="correction_reference"):
        registry.respond(
            appeal["appeal_id"], reviewer_ref="reviewer-1", outcome="CORRECTED",
            response="Correction approved.", reviewer_authorized=True,
        )

    answered = registry.respond(
        appeal["appeal_id"], reviewer_ref="reviewer-1", outcome="CORRECTED",
        response="A separate correction record was created.",
        reviewer_authorized=True, correction_reference="correction-ref-001",
    )
    assert answered["correction_reference"] == "correction-ref-001"
    assert answered["case_id"] == "CASE-SYNTHETIC-001"


def test_invalid_appeal_input_and_wrong_data_mode_fail_without_partial_record():
    registry = CitizenAppealRegistry()
    with pytest.raises(ValueError, match="synthetic data only"):
        registry.submit(
            case_id="CASE-REAL-001", citizen_ref="citizen-ref",
            request_type="REVIEW", reason="real data request", data_mode="real",
        )
    with pytest.raises(ValueError, match="request_type"):
        registry.submit(
            case_id="CASE-1", citizen_ref="citizen-ref",
            request_type="BLOCK", reason="unsupported request",
        )
    assert registry._appeals == {}


def test_appeal_records_are_returned_as_detached_copies():
    registry = CitizenAppealRegistry()
    appeal = _submitted(registry)
    appeal["timeline"].clear()

    stored = registry.get(appeal["appeal_id"])
    assert stored["timeline"][0]["event"] == "SUBMITTED"
