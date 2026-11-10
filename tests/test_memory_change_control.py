import pytest

from finzanjir_ai.memory.control import KnowledgeChangeControl


def test_ai_can_propose_but_not_directly_write_authoritative_knowledge():
    control = KnowledgeChangeControl(current_version="v0.6")
    candidate = control.propose(statement="New candidate knowledge", provenance=("source-a",))
    assert candidate["status"] == "PENDING_REVIEW"
    assert candidate["target_version"] == "v0.7-candidate"

    with pytest.raises(PermissionError):
        control.write_authoritative(candidate)


def test_candidate_requires_explicit_review_to_approve():
    control = KnowledgeChangeControl(current_version="v0.6")
    candidate = control.propose(statement="Reviewed candidate", provenance=("source-b",))
    approved = control.approve(candidate["candidate_id"], reviewer_id="reviewer-1")
    assert approved["status"] == "APPROVED"
    assert approved["reviewer_id"] == "reviewer-1"
    assert approved["target_version"] == "v0.7"
