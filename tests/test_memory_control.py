import pytest

from finzanjir_ai.memory.control import KnowledgeChangeControl


def test_candidate_knowledge_requires_reviewer_approval_before_authoritative_change():
    control = KnowledgeChangeControl(current_version="v0.6")
    candidate = control.propose(statement="Candidate fact", provenance=("source-a",))

    assert candidate["status"] == "PENDING_REVIEW"
    with pytest.raises(PermissionError):
        control.write_authoritative(candidate)

    approved = control.approve(candidate["candidate_id"], reviewer_id="reviewer-1")
    assert approved["status"] == "APPROVED"
    assert approved["target_version"] == "v0.7"


def test_ai_candidate_cannot_become_authoritative_without_review():
    control = KnowledgeChangeControl(current_version="v0.6")
    candidate = control.propose(statement="Candidate fact", provenance=("source-a",))
    with pytest.raises(PermissionError):
        control.write_authoritative(candidate)
