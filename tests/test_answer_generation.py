from finzanjir_ai.answer.generator import generate_grounded_answer


def test_grounded_answer_uses_evidence_and_provenance():
    result = generate_grounded_answer(
        question="Why is this signal important?",
        knowledge=[{"record_id": "ck-1", "statement": "Evidence supports risk assessment.", "provenance": ["source-a"]}],
        runtime=[{"type": "Signal", "id": "sig-1", "status": "ACTIVE"}],
    )
    assert result.abstained is False
    assert result.confidence > 0
    assert "ck-1" in result.knowledge_refs
    assert "source-a" in result.provenance


def test_answer_abstains_without_grounding_context():
    result = generate_grounded_answer(question="Unknown?", knowledge=[], runtime=[])
    assert result.abstained is True
    assert result.confidence == 0.0
