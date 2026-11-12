from finzanjir_ai.knowledge_governance import KnowledgeGovernance


def test_answer_is_bound_to_source():
    result = KnowledgeGovernance().answer(
        claim="case status is OPEN",
        source="case-record-v1",
        evidence_sufficient=True,
    )

    assert result["claim"] == "case status is OPEN"
    assert result["source"] == "case-record-v1"
    assert result["status"] == "supported"


def test_insufficient_source_is_explicitly_limited():
    result = KnowledgeGovernance().answer(
        claim="the user committed fraud",
        source=None,
        evidence_sufficient=False,
    )

    assert result["status"] == "insufficient_evidence"
    assert result["claim"] is None
    assert result["limitation"]


def test_conflicting_sources_are_not_hidden():
    result = KnowledgeGovernance().answer(
        claim="case status is CLOSED",
        source="source-a",
        evidence_sufficient=True,
        conflicting_sources=["source-b"],
    )

    assert result["status"] == "conflict"
    assert result["conflicting_sources"] == ["source-b"]
    assert result["limitation"]


def test_candidate_knowledge_cannot_become_authoritative_without_approval():
    result = KnowledgeGovernance().promote_candidate(
        candidate={"claim": "new fact"},
        authorized=False,
    )

    assert result["approved"] is False
    assert result["status"] == "approval_required"
