import pytest

from finzanjir_ai.memory.control import KnowledgeChangeControl


def test_candidate_knowledge_requires_approval_before_authoritative_commit():
    control = KnowledgeChangeControl()
    candidate_id = control.submit_candidate({"statement": "Candidate fact"}, submitted_by="ai")
    assert control.get(candidate_id)["status"] == "PENDING"
    with pytest.raises(PermissionError):
        control.approve(candidate_id, actor_role="ai")
    approved = control.approve(candidate_id, actor_role="knowledge_reviewer")
    assert approved["status"] == "APPROVED"


def test_ai_cannot_write_authoritative_knowledge_directly():
    control = KnowledgeChangeControl()
    with pytest.raises(PermissionError):
        control.write_authoritative({"statement": "Forbidden"}, actor_role="ai")
