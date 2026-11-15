from benchmarks.run_complex_question_diagnostics import run_diagnostics


def test_diagnostic_runner_scores_oracle_subquestion_retrieval_without_external_evidence():
    benchmark = {
        "benchmark_id": "unit_test",
        "version": 1,
        "corpus_version": "canonical_knowledge_v0.6",
        "cases": [
            {
                "id": "case_1",
                "query": "How does fraud protection work?",
                "language": "en",
                "subquestions": [
                    {
                        "id": "a",
                        "retrieval_query": "fraud risk protection",
                        "evidence_scope": "canonical_project",
                        "knowledge_state": "must_be_resolved_from_corpus",
                        "expected_evidence_ids": ["ck_test_1"],
                    },
                    {
                        "id": "b",
                        "retrieval_query": "",
                        "evidence_scope": "external_research",
                        "knowledge_state": "unknown_until_researched",
                        "expected_evidence_ids": [],
                    },
                ],
            }
        ],
    }
    corpus = {
        "records": [
            {
                "id": "ck_test_1",
                "canonical_concept_id": "concept_test",
                "statement": "Fraud risk protection uses verified evidence and review.",
                "aliases": [],
                "evidence": {"status": "source_derived"},
                "provenance": {"source_sections": ["synthetic test"]},
            }
        ]
    }

    report = run_diagnostics(benchmark, corpus, top_k=5)

    assert report["diagnostic_scope"] == "retrieval_only_with_oracle_subquestion_decomposition"
    assert report["scored_subquestion_count"] == 1
    assert report["unscored_subquestion_count"] == 1
    assert report["missing_expected_record_ids"] == []
    scored = report["results"][0]
    assert scored["subquestion_baseline"]["recall_at_k"] == 1.0
    assert scored["subquestion_expanded"]["recall_at_k"] == 1.0
    assert report["results"][1]["status"] == "not_scored_no_canonical_evidence_expected"
