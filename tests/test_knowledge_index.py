from finzanjir_ai.knowledge.index import build_knowledge_index, normalize_record


def test_normalize_record_preserves_identity_concept_statement_and_provenance():
    record = {
        "id": "ck_000001",
        "concept_id": "concept_1",
        "canonical_concept_id": "concept_1",
        "statement": "Fraud signal requires evidence.",
        "aliases": ["fraud signal", "suspicious signal"],
        "evidence": {"status": "supported"},
        "provenance": [{"source": "source-a"}],
        "reconciliation": {"status": "canonical"},
    }

    normalized = normalize_record(record)

    assert normalized.record_id == "ck_000001"
    assert normalized.concept_id == "concept_1"
    assert normalized.statement == "Fraud signal requires evidence."
    assert normalized.aliases == ("fraud signal", "suspicious signal")
    assert normalized.provenance == ({"source": "source-a"},)


def test_index_supports_exact_term_and_concept_lookup():
    records = [
        {
            "id": "ck_1", "concept_id": "c1", "canonical_concept_id": "c1",
            "statement": "Fraud signal requires evidence.",
            "aliases": ["suspicious signal"], "evidence": {}, "provenance": [], "reconciliation": {},
        },
        {
            "id": "ck_2", "concept_id": "c2", "canonical_concept_id": "c2",
            "statement": "Evidence supports risk assessment.",
            "aliases": ["risk evidence"], "evidence": {}, "provenance": [], "reconciliation": {},
        },
    ]

    index = build_knowledge_index(records)

    assert index.record_ids_for_term("evidence") == ("ck_1", "ck_2")
    assert index.record_ids_for_concept("c1") == ("ck_1",)
    assert index.record_ids_for_term("suspicious") == ("ck_1",)
